"""Independent help acknowledgements over the existing, read-only device inbox.

No payment workflow, risk state, challenge, signing key, or delivery assumption.
SQLite transactions serialize responses/cancellation and retain rejected actions.
"""
from contextlib import contextmanager, closing
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import sqlite3


def utc_now():
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class HelpPrincipal:
    role: str
    actor_id: str
    device_ids: tuple[str, ...]


class HelpNotFound(ValueError):
    pass


class HelpStore:
    def __init__(self, inbox_path, database, routes):
        self.inbox = Path(inbox_path).resolve().as_uri() + '?mode=ro'
        self.database = str(database)
        self.routes = {device: dict(route) for device, route in routes.items()}
        if not self.routes or any(set(route) != {'owner', 'contact'} or not all(route.values())
                                  for route in self.routes.values()):
            raise ValueError('explicit device owner/contact routes required')
        with self.db() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS help_requests (
                    event_id TEXT PRIMARY KEY, device_id TEXT NOT NULL,
                    owner_id TEXT NOT NULL, contact_id TEXT NOT NULL,
                    received_at TEXT NOT NULL, imported_at TEXT NOT NULL,
                    status TEXT NOT NULL CHECK(status IN ('recorded','accepted','unable_to_help','cancelled')),
                    version INTEGER NOT NULL DEFAULT 0);
                CREATE TABLE IF NOT EXISTS help_audit (
                    seq INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT NOT NULL REFERENCES help_requests(event_id),
                    action_id TEXT UNIQUE, actor_role TEXT NOT NULL, actor_id TEXT NOT NULL,
                    command TEXT NOT NULL, before_state TEXT, after_state TEXT NOT NULL,
                    result TEXT NOT NULL, reason TEXT, at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS help_sync (id INTEGER PRIMARY KEY CHECK(id=1), cursor INTEGER NOT NULL);
                INSERT OR IGNORE INTO help_sync VALUES (1,0);
            ''')
        self.last_sync = None
        self.sync()

    @contextmanager
    def db(self):
        db = sqlite3.connect(self.database, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA foreign_keys=ON')
        try:
            with db:
                yield db
        finally:
            db.close()

    def sync(self):
        # Lock only the new database; hold no source lock while writing audit.
        while True:
            with self.db() as db:
                db.execute('BEGIN IMMEDIATE')
                cursor = db.execute('SELECT cursor FROM help_sync WHERE id=1').fetchone()[0]
                with closing(sqlite3.connect(self.inbox, uri=True, timeout=5)) as source:
                    source.row_factory = sqlite3.Row
                    events = source.execute('SELECT rowid AS inbox_row, * FROM device_events WHERE rowid>? ORDER BY rowid LIMIT 500', (cursor,)).fetchall()
                for event in events:
                    route = self.routes.get(event['device_id'])
                    if event['event_type'] != 'help_request' or route is None:
                        continue
                    stamp = utc_now()
                    inserted = db.execute('INSERT OR IGNORE INTO help_requests VALUES (?,?,?,?,?,?,?,0)',
                        (event['event_id'],event['device_id'],route['owner'],route['contact'],event['received_at'],stamp,'recorded')).rowcount
                    if inserted:
                        db.execute('INSERT INTO help_audit (event_id,action_id,actor_role,actor_id,command,before_state,after_state,result,reason,at) VALUES (?,NULL,?,?,?,?,?,?,NULL,?)',
                            (event['event_id'],'source','device-inbox','record',None,'recorded','applied',stamp))
                if events:
                    db.execute('UPDATE help_sync SET cursor=? WHERE id=1',(events[-1]['inbox_row'],))
            if len(events) < 500:
                self.last_sync = utc_now()
                return

    @staticmethod
    def allowed(row, principal):
        if row['device_id'] not in principal.device_ids:
            return False
        return (principal.role == 'dashboard' or
                principal.role == 'owner' and row['owner_id'] == principal.actor_id or
                principal.role == 'contact' and row['contact_id'] == principal.actor_id)

    def find(self, db, event_id, principal):
        row = db.execute('SELECT * FROM help_requests WHERE event_id=?',(event_id,)).fetchone()
        if row is None or not self.allowed(row, principal):
            raise HelpNotFound('help request not found')
        return row

    def view(self, db, row):
        return {**dict(row), 'history':[dict(action) for action in db.execute(
            'SELECT * FROM help_audit WHERE event_id=? ORDER BY seq',(row['event_id'],))]}

    def get(self, event_id, principal):
        self.sync()
        with self.db() as db:
            return self.view(db, self.find(db,event_id,principal))

    def list(self, principal):
        self.sync()
        with self.db() as db:
            # Filter in SQL before LIMIT so other devices cannot crowd out this role.
            devices = ','.join('?' for _ in principal.device_ids)
            params = list(principal.device_ids)
            field = {'owner':'owner_id','contact':'contact_id'}.get(principal.role)
            condition = '' if field is None else f' AND {field}=?'
            if field:
                params.append(principal.actor_id)
            rows=db.execute(f'SELECT * FROM help_requests WHERE device_id IN ({devices}){condition} ORDER BY rowid DESC LIMIT 100',params).fetchall()
            return [self.view(db,row) for row in rows]

    def act(self, event_id, action_id, principal, command):
        if (command not in {'accept','unable','cancel'} or
                command == 'cancel' and principal.role != 'owner' or
                command != 'cancel' and principal.role != 'contact'):
            raise PermissionError('this role cannot perform that action')
        self.sync()
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            row = self.find(db,event_id,principal)
            existing = db.execute('SELECT * FROM help_audit WHERE action_id=?',(action_id,)).fetchone()
            if existing is not None:
                matches = (existing['event_id']==event_id and existing['actor_role']==principal.role
                           and existing['actor_id']==principal.actor_id and existing['command']==command)
                if not matches:
                    return 409, {'error':'ACTION_ID_CONFLICT','detail':'This action ID was already used for different content.'}
                return (200 if existing['result']=='applied' else 409), {
                    'duplicate':True,'action':dict(existing),'request':self.view(db,row)}
            before=row['status']
            valid = before!='cancelled' if command=='cancel' else before=='recorded'
            after = {'accept':'accepted','unable':'unable_to_help','cancel':'cancelled'}[command] if valid else before
            result = 'applied' if valid else 'rejected'
            reason = None if valid else 'TRANSITION_NOT_ALLOWED'
            db.execute('INSERT INTO help_audit (event_id,action_id,actor_role,actor_id,command,before_state,after_state,result,reason,at) VALUES (?,?,?,?,?,?,?,?,?,?)',
                (event_id,action_id,principal.role,principal.actor_id,command,before,after,result,reason,utc_now()))
            if valid:
                db.execute('UPDATE help_requests SET status=?,version=version+1 WHERE event_id=?',(after,event_id))
            updated=self.find(db,event_id,principal)
            action=dict(db.execute('SELECT * FROM help_audit WHERE action_id=?',(action_id,)).fetchone())
            return (200 if valid else 409), {'duplicate':False,'action':action,'request':self.view(db,updated)}
