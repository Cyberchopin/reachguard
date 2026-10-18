"""Independent help acknowledgements over the existing, read-only device inbox.

No payment workflow, risk state, challenge, signing key, or delivery assumption.
SQLite transactions serialize responses/cancellation and retain rejected actions.

Optional rotation: a route with an ordered `contacts` schedule notifies one
contact at a time. After `wait_seconds` with no acceptance the next entry is
notified, and after the last one the rotation starts again from the first, until
someone accepts or the owner cancels. A contact may appear more than once in the
schedule (e.g. close family several times per round). Status stays `recorded` while rotating; the
rotation lives in its own tables and every notify/timeout is audited. Requests
recorded before rotation was configured keep the single-contact behaviour.
"""
from contextlib import contextmanager, closing
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sqlite3
from .reach_observability import observed, operation


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
    def __init__(self, inbox_path, database, routes, wait_seconds=20, now=None):
        self.inbox = Path(inbox_path).resolve().as_uri() + '?mode=ro'
        self.database = str(database)
        self.routes = {device: dict(route) for device, route in routes.items()}
        if not self.routes or any(set(route) - {'contacts'} != {'owner', 'contact'} or not all(route.values())
                                  for route in self.routes.values()):
            raise ValueError('explicit device owner/contact routes required')
        for route in self.routes.values():
            if 'contacts' in route:
                contacts = list(route['contacts'])
                if not contacts or not all(contacts) or contacts[0] != route['contact']:
                    raise ValueError('rotation contacts must be non-empty and start with the route contact')
                route['contacts'] = contacts
        if wait_seconds <= 0:
            raise ValueError('rotation wait must be positive')
        self.wait = timedelta(seconds=wait_seconds)
        self.now = now or (lambda: datetime.now(timezone.utc))
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
                CREATE TABLE IF NOT EXISTS help_rotation (
                    event_id TEXT PRIMARY KEY REFERENCES help_requests(event_id),
                    contacts TEXT NOT NULL, position INTEGER NOT NULL, round INTEGER NOT NULL,
                    next_due_at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS help_notified (
                    event_id TEXT NOT NULL REFERENCES help_requests(event_id), contact_id TEXT NOT NULL,
                    PRIMARY KEY (event_id, contact_id));
                CREATE TABLE IF NOT EXISTS help_declined (
                    event_id TEXT NOT NULL REFERENCES help_requests(event_id), contact_id TEXT NOT NULL,
                    PRIMARY KEY (event_id, contact_id));
            ''')
        self.last_sync = None
        self.sync()

    @contextmanager
    def db(self):
        db = sqlite3.connect(self.database, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA foreign_keys=ON')
        try:
            with operation('help.persist'), db:
                yield db
        finally:
            db.close()

    @observed('help.sync')
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
                        if 'contacts' in route:
                            self.start_rotation(db, event['event_id'], route['contacts'])
                if events:
                    db.execute('UPDATE help_sync SET cursor=? WHERE id=1',(events[-1]['inbox_row'],))
            if len(events) < 500:
                self.rotate()
                self.last_sync = utc_now()
                return

    def notify(self, db, event_id, contacts, position, round_, at):
        contact = contacts[position]
        db.execute('INSERT OR IGNORE INTO help_notified VALUES (?,?)', (event_id, contact))
        db.execute('INSERT INTO help_audit (event_id,action_id,actor_role,actor_id,command,before_state,after_state,result,reason,at) VALUES (?,NULL,?,?,?,?,?,?,?,?)',
            (event_id,'system',contact,'notify','recorded','recorded','applied',f'round {round_}, step {position + 1} of {len(contacts)}',at.isoformat()))
        db.execute('UPDATE help_rotation SET position=?,round=?,next_due_at=? WHERE event_id=?',
            (position, round_, (at + self.wait).isoformat(), event_id))

    def start_rotation(self, db, event_id, contacts):
        at = self.now()
        db.execute('INSERT INTO help_rotation VALUES (?,?,0,1,?)', (event_id, json.dumps(contacts), at.isoformat()))
        self.notify(db, event_id, contacts, 0, 1, at)

    def step(self, db, rotation, at):
        contacts = json.loads(rotation['contacts'])
        db.execute('INSERT INTO help_audit (event_id,action_id,actor_role,actor_id,command,before_state,after_state,result,reason,at) VALUES (?,NULL,?,?,?,?,?,?,?,?)',
            (rotation['event_id'],'system',contacts[rotation['position']],'timeout','recorded','recorded','applied',
             f'no acceptance within {int(self.wait.total_seconds())} s',at.isoformat()))
        self.advance(db, rotation, at)

    def advance(self, db, rotation, at):
        # Notify the next scheduled contact, skipping anyone who answered unable.
        contacts = json.loads(rotation['contacts'])
        declined = self.declined(db, rotation['event_id'])
        position, round_ = rotation['position'], rotation['round']
        for _ in contacts:
            position = (position + 1) % len(contacts)
            round_ += position == 0
            if contacts[position] not in declined:
                break
        self.notify(db, rotation['event_id'], contacts, position, round_, at)

    @staticmethod
    def declined(db, event_id):
        return {r['contact_id'] for r in db.execute('SELECT contact_id FROM help_declined WHERE event_id=?', (event_id,))}

    @observed('help.rotate')
    def rotate(self):
        # One step per overdue request per pass: after downtime the rotation
        # resumes where it stopped instead of replaying every missed step.
        at = self.now()
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            due = db.execute("SELECT o.* FROM help_rotation o JOIN help_requests r USING(event_id) WHERE r.status='recorded' AND o.next_due_at<=?",
                (at.isoformat(),)).fetchall()
            for rotation in due:
                self.step(db, rotation, at)

    @staticmethod
    def allowed(db, row, principal):
        if row['device_id'] not in principal.device_ids:
            return False
        return (principal.role == 'dashboard' or
                principal.role == 'owner' and row['owner_id'] == principal.actor_id or
                principal.role == 'contact' and (row['contact_id'] == principal.actor_id or
                    db.execute('SELECT 1 FROM help_notified WHERE event_id=? AND contact_id=?',
                               (row['event_id'], principal.actor_id)).fetchone() is not None))

    def find(self, db, event_id, principal):
        row = db.execute('SELECT * FROM help_requests WHERE event_id=?',(event_id,)).fetchone()
        if row is None or not self.allowed(db, row, principal):
            raise HelpNotFound('help request not found')
        return row

    def view(self, db, row):
        rotation = db.execute('SELECT * FROM help_rotation WHERE event_id=?',(row['event_id'],)).fetchone()
        if rotation is not None:
            contacts = json.loads(rotation['contacts'])
            rotation = {'contacts':contacts,'round':rotation['round'],'position':rotation['position'],
                        'current_contact':contacts[rotation['position']],'next_due_at':rotation['next_due_at']}
        return {**dict(row), 'rotation':rotation, 'history':[dict(action) for action in db.execute(
            'SELECT * FROM help_audit WHERE event_id=? ORDER BY seq',(row['event_id'],))]}

    @observed('help.read')
    def get(self, event_id, principal):
        self.sync()
        with self.db() as db:
            return self.view(db, self.find(db,event_id,principal))

    @observed('help.list')
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
            if principal.role == 'contact':
                condition = ' AND (contact_id=? OR event_id IN (SELECT event_id FROM help_notified WHERE contact_id=?))'
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
            reason = None if valid else 'TRANSITION_NOT_ALLOWED'
            rotation = db.execute('SELECT * FROM help_rotation WHERE event_id=?',(event_id,)).fetchone()
            passed_on = False
            if command=='unable' and valid and rotation is not None:
                # With rotation, unable passes the request to the next contact;
                # it ends only when every contact in the schedule has declined.
                declined = self.declined(db, event_id)
                if principal.actor_id in declined:
                    valid, after, reason = False, before, 'ALREADY_DECLINED'
                else:
                    db.execute('INSERT INTO help_declined VALUES (?,?)', (event_id, principal.actor_id))
                    if set(json.loads(rotation['contacts'])) - declined - {principal.actor_id}:
                        after, reason, passed_on = 'recorded', 'passed to the next contact', True
            result = 'applied' if valid else 'rejected'
            db.execute('INSERT INTO help_audit (event_id,action_id,actor_role,actor_id,command,before_state,after_state,result,reason,at) VALUES (?,?,?,?,?,?,?,?,?,?)',
                (event_id,action_id,principal.role,principal.actor_id,command,before,after,result,reason,utc_now()))
            if passed_on:
                self.advance(db, rotation, self.now())
            elif valid:
                db.execute('UPDATE help_requests SET status=?,version=version+1 WHERE event_id=?',(after,event_id))
            updated=self.find(db,event_id,principal)
            action=dict(db.execute('SELECT * FROM help_audit WHERE action_id=?',(action_id,)).fetchone())
            return (200 if valid else 409), {'duplicate':False,'action':action,'request':self.view(db,updated)}

