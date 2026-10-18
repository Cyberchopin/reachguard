"""Opt-in, local-only intent adapter; device input never carries authority.

Read the existing inbox with SQLite mode=ro. Persist claims before issuing a
challenge: interruption may lose liveness but never retries the same event.
"""
import json
import sqlite3
import threading
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

from fastapi import Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import Field

from .models import StrictModel
from .review_transport import ContactOperation, bearer, ASSETS


def now():
    return datetime.now(timezone.utc).isoformat()


class Binding(ContactOperation):
    session_id: str = Field(min_length=1, max_length=64)
    device_id: str = Field(min_length=1, max_length=64, pattern=r'^[A-Za-z0-9_.:-]+$')
    claimed_identity: str = Field(min_length=1, max_length=80, pattern=r'^[A-Za-z0-9_-]+$')


class SelectedEvent(StrictModel):
    event_id: str = Field(min_length=1, max_length=128)


class DeviceFusion:
    def __init__(self, workflow, inbox_path, state_path):
        self.workflow = workflow
        self.inbox_uri = Path(inbox_path).resolve().as_uri() + '?mode=ro'
        self.state_path = str(state_path)
        self.lock = threading.RLock()
        self.binding = None
        with closing(self.state()) as db, db:
            db.execute('CREATE TABLE IF NOT EXISTS fusion_events (event_id TEXT PRIMARY KEY, record TEXT NOT NULL)')
        # Verify the inbox exists without creating or modifying it.
        self.events()

    def state(self):
        return sqlite3.connect(self.state_path, timeout=10)

    def events(self):
        with closing(sqlite3.connect(self.inbox_uri, uri=True, timeout=5)) as db:
            db.row_factory = sqlite3.Row
            return [dict(row) for row in db.execute('SELECT * FROM device_events ORDER BY rowid DESC LIMIT 100')]

    def event(self, event_id):
        with closing(sqlite3.connect(self.inbox_uri, uri=True, timeout=5)) as db:
            db.row_factory = sqlite3.Row
            row = db.execute('SELECT * FROM device_events WHERE event_id=?', (event_id,)).fetchone()
            if row is None:
                raise ValueError('event not found')
            return dict(row)

    def reason(self, event):
        if event['event_type'] == 'help_request':
            return '求助意图；不会创建核验请求'
        if self.binding is None:
            return '尚未绑定 CallGate 会话、设备、联系人和模拟操作'
        b = self.binding
        context = self.workflow.binding_context()
        if context['session_id'] != b.session_id:
            return '绑定会话已结束；请重新绑定当前会话'
        if event['device_id'] != b.device_id:
            return '事件设备与绑定设备不匹配'
        if not context['processing_allowed']:
            return '当前会话尚未同意处理测试内容'
        if context['risk_state'] != 'CHALLENGED':
            return '当前 policy 状态为 ' + context['risk_state'] + '；只有 CHALLENGED 可申请核验'
        if context['authorization_denied']:
            return '当前会话授权已被拒绝或过期'
        if context['pending']:
            return '已有待回应核验请求；不会覆盖'
        return None

    def bind(self, binding):
        with self.lock:
            if binding.session_id != self.workflow.binding_context()['session_id']:
                raise ValueError('session changed; reload before binding')
            if binding.claimed_identity not in self.workflow.contact_identities():
                raise ValueError('unknown saved contact; no fallback')
            self.binding = binding
            return binding.model_dump()

    def load(self, db, event_id):
        row = db.execute('SELECT record FROM fusion_events WHERE event_id=?', (event_id,)).fetchone()
        return None if row is None else json.loads(row[0])

    def save(self, db, record):
        db.execute('UPDATE fusion_events SET record=? WHERE event_id=?',
                   (json.dumps(record), record['event']['event_id']))

    def process(self, event_id, *, audio_active=False):
        with self.lock, closing(self.state()) as db:
            existing = self.load(db, event_id)
            if existing is not None:
                return existing
            event = self.event(event_id)
            reason = self.reason(event)
            if reason:
                return {'event':event, 'status':'not_created', 'reason':reason}
            if audio_active:
                return {'event':event, 'status':'not_created', 'reason':'请先停止录音，再申请核验'}
            record = {'event':event, 'binding':self.binding.model_dump(), 'status':'claimed',
                      'timeline':[{'stage':'event_received', 'at':event['received_at']}],
                      'reason':'创建结果尚未确认；该事件不会自动重试'}
            try:
                db.execute('INSERT INTO fusion_events VALUES (?, ?)', (event_id, json.dumps(record)))
                db.commit()
            except sqlite3.IntegrityError:
                return self.load(db, event_id)
            try:
                b = self.binding
                result = self.workflow.request_bound_confirmation(session_id=b.session_id,
                    destination=b.destination, amount_cents=b.amount_cents, claimed_identity=b.claimed_identity)
                record.update(status='request_created', reason=None,
                              request=result['request'].model_dump(),
                              out_of_band_challenge=result['out_of_band_challenge'])
                record['timeline'].append({'stage':'verification_request_created', 'at':now(),
                                           'request_id':result['request'].request_id})
            except ValueError as error:
                record.update(status='refused', reason=str(error))
            self.save(db, record)
            db.commit()
            return record

    def record_completion(self, decision, result):
        with self.lock, closing(self.state()) as db:
            for event_id, raw in db.execute('SELECT event_id, record FROM fusion_events').fetchall():
                record = json.loads(raw)
                if record.get('request', {}).get('request_id') != decision.request.request_id:
                    continue
                if any(row['stage'] == 'contact_responded' for row in record['timeline']):
                    return
                record['timeline'].append({'stage':'contact_responded', 'at':now(),
                    'approved':decision.approved, 'reviewer':decision.request.reviewer})
                record['timeline'].append({'stage':'simulated_operation_result', 'at':now(), 'result':result})
                record.update(status='completed', outcome=result)
                record.pop('out_of_band_challenge', None)
                self.save(db, record)
                db.commit()
                return

    def snapshot(self):
        with self.lock, closing(self.state()) as db:
            records = {event_id:json.loads(raw) for event_id, raw in db.execute('SELECT event_id, record FROM fusion_events')}
            pending = self.workflow.pending_confirmation()
            context = self.workflow.binding_context()
            for record in records.values():
                if record['status'] == 'request_created' and (
                    pending is None or pending['request']['request_id'] != record['request']['request_id']):
                    record = dict(record)
                    record.update(status='no_longer_pending', reason='请求已失效、取消或服务重启；没有已记录的联系人回应，不会重新创建')
                    record.pop('out_of_band_challenge', None)
                    records[record['event']['event_id']] = record
            rows = []
            for event in self.events():
                rows.append(records.get(event['event_id']) or {'event':event,
                    'status':'intent_received', 'reason':self.reason(event),
                    'timeline':[{'stage':'event_received','at':event['received_at']}]})
            return {'context':context, 'contacts':self.workflow.contact_identities(),
                    'binding':None if self.binding is None else self.binding.model_dump(), 'events':rows,
                    'intent_only':True}


def attach_device_fusion(app, workflow, participant_token, inbox_path, state_path, *, audio_active=lambda:False):
    fusion = DeviceFusion(workflow, inbox_path, state_path)
    app.state.device_fusion = fusion
    participant = bearer(participant_token)

    @app.get('/fusion')
    def page():
        return FileResponse(ASSETS/'device-fusion.html')

    @app.get('/device-fusion.js')
    def javascript():
        return FileResponse(ASSETS/'device-fusion.js', media_type='text/javascript')

    @app.get('/api/fusion', dependencies=[Depends(participant)])
    def snapshot():
        return fusion.snapshot()

    @app.post('/api/fusion/binding', dependencies=[Depends(participant)])
    def bind(body: Binding):
        try:
            return fusion.bind(body)
        except ValueError as error:
            raise HTTPException(409, str(error)) from None

    @app.post('/api/fusion/process', dependencies=[Depends(participant)])
    def process(body: SelectedEvent):
        try:
            return fusion.process(body.event_id, audio_active=audio_active())
        except ValueError as error:
            raise HTTPException(409, str(error)) from None

    return fusion
