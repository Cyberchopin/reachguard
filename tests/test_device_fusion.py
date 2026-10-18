import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient
from callgate.device_fusion import Binding, DeviceFusion
from callgate.review_transport import create_broker_app, create_reviewer_app, SubmittedDecision
from callgate.models import Transcript
from tests.test_contact_binding import setup


@pytest.fixture
def demo(tmp_path):
    inbox, state = tmp_path/'inbox.db', tmp_path/'fusion.db'
    with sqlite3.connect(inbox) as db:
        db.execute('CREATE TABLE device_events (event_id TEXT PRIMARY KEY, device_id TEXT, event_type TEXT, received_at TEXT)')
        db.executemany('INSERT INTO device_events VALUES (?,?,?,?)', [
            ('verify-1','nano-01','verify_request','2026-10-17T01:00:00+00:00'),
            ('verify-2','nano-01','verify_request','2026-10-17T01:00:01+00:00'),
            ('help-1','nano-01','help_request','2026-10-17T01:00:02+00:00'),
            ('other','nano-02','verify_request','2026-10-17T01:00:03+00:00')])
    workflow, family, bank, clock = setup()
    app = create_broker_app(workflow, 'operator', {'family':'family-role','bank':'bank-role'},
                            device_inbox=inbox, fusion_state=state)
    client = TestClient(app, base_url='http://127.0.0.1:8766')
    client.headers['Authorization']='Bearer operator'
    return workflow, app.state.device_fusion, client, family, bank, clock, inbox, state


def bind(workflow, client, **changes):
    body = dict(session_id=workflow.binding_context()['session_id'], device_id='nano-01',
                claimed_identity='saved-family',destination='fictional-wallet',amount_cents=100)
    return client.post('/api/fusion/binding',json={**body,**changes})


def process(client, event_id='verify-1'):
    return client.post('/api/fusion/process',json={'event_id':event_id})


@pytest.mark.parametrize('approved', [True, False])
def test_original_signed_reviewer_roundtrip_and_actual_timeline(demo, approved):
    workflow, fusion, client, key, *_ = demo
    assert bind(workflow, client).status_code == 200
    record = process(client).json()
    assert record['status']=='request_created'
    assert [t['stage'] for t in record['timeline']]==['event_received','verification_request_created']
    request_id = record['request']['request_id']
    # Exercise the unchanged reviewer validation, signing and broker decision route.
    def pending():
        return client.get('/api/review/pending',headers={'Authorization':'Bearer family-role'}).json()
    def submit(body):
        response=client.post('/api/review/decision',headers={'Authorization':'Bearer family-role'},json=body.model_dump())
        assert response.status_code==200
        return response.json()
    reviewer = TestClient(create_reviewer_app(key,'family-role',pending,submit,
        expected_reviewer='family'),base_url='http://127.0.0.1:8767')
    result=reviewer.post('/api/decide',headers={'Authorization':'Bearer family-role'},json={
        'request_id':request_id,'approved':approved,'challenge_response':record['out_of_band_challenge']})
    assert result.status_code==200
    assert result.json()['status']==('simulated_action_completed' if approved else 'reviewer_denied')
    row=next(r for r in client.get('/api/fusion').json()['events'] if r['event']['event_id']=='verify-1')
    assert [t['stage'] for t in row['timeline']]==['event_received','verification_request_created','contact_responded','simulated_operation_result']
    assert row['timeline'][2]['approved'] is approved
    assert 'out_of_band_challenge' not in row
    assert process(client).json()['request']['request_id']==request_id
    assert reviewer.post('/api/decide',headers={'Authorization':'Bearer family-role'},json={
        'request_id':request_id,'approved':approved,'challenge_response':record['out_of_band_challenge']}).status_code==409


def test_binding_refusals_help_and_no_pending_replacement(demo):
    workflow, fusion, client, *_ = demo
    assert '尚未绑定' in process(client).json()['reason']
    assert bind(workflow, client,claimed_identity='unknown').status_code==409
    assert bind(workflow, client).status_code==200
    assert '不匹配' in process(client,'other').json()['reason']
    assert '求助意图' in process(client,'help-1').json()['reason']
    one=process(client).json()
    assert '已有待回应' in process(client,'verify-2').json()['reason']
    assert workflow.pending_confirmation()['request']['request_id']==one['request']['request_id']
    with sqlite3.connect(demo[-2]) as db:
        assert db.execute('SELECT count(*) FROM device_events').fetchone()[0]==4


@pytest.mark.parametrize('mode',['unverified','blocked','cooling','consent','reset','audio'])
def test_current_policy_and_session_guards(demo, mode):
    workflow, fusion, client, *_ = demo
    bind(workflow,client)
    if mode=='reset':
        workflow.reset_session()
    elif mode=='consent':
        workflow.set_processing_consent(False)
    elif mode=='unverified':
        workflow.reset_session(); workflow.set_processing_consent(True); bind(workflow,client)
    elif mode=='blocked':
        workflow.ingest(Transcript(segment_id='s2',text='Read me your password.',start_ms=1,end_ms=2,final=True))
    elif mode=='cooling':
        workflow.ingest(Transcript(segment_id='s2',text='Do not tell anyone.',start_ms=1,end_ms=2,final=True))
    if mode=='audio':
        result=fusion.process('verify-1',audio_active=True)
    else:
        result=process(client).json()
    assert result['status']=='not_created' and result['reason']
    assert workflow.pending_confirmation() is None


def test_atomic_stale_binding_and_concurrent_duplicate_claims(demo):
    workflow, fusion, client, *_ = demo
    bind(workflow,client)
    with ThreadPoolExecutor(max_workers=8) as pool:
        records=list(pool.map(lambda _: fusion.process('verify-1'),range(16)))
    assert len({r['request']['request_id'] for r in records})==1
    assert len(workflow._issued)==1
    session=workflow.binding_context()['session_id']
    workflow.reset_session()
    with pytest.raises(ValueError,match='session changed'):
        workflow.request_bound_confirmation(session_id=session,destination='x',amount_cents=1,claimed_identity='saved-family')


def test_persistent_claim_after_restart_and_unknown_completion_not_fabricated(demo):
    workflow, fusion, client, _, _, clock, inbox, state = demo
    bind(workflow,client)
    record=process(client).json()
    clock[0]=record['request']['expires_at']
    row=next(r for r in fusion.snapshot()['events'] if r['event']['event_id']=='verify-1')
    assert row['status']=='no_longer_pending'
    assert len(row['timeline'])==2
    new_workflow, *_=setup()
    restarted=DeviceFusion(new_workflow,inbox,state)
    assert restarted.process('verify-1')['request']['request_id']==record['request']['request_id']
    assert new_workflow.pending_confirmation() is None
    assert restarted.binding is None


def test_auth_loopback_boundaries_and_unchanged_broker_default(demo):
    workflow, fusion, client, *_=demo
    assert client.get('/fusion').status_code==200
    assert client.get('/fusion').headers['content-type'].startswith('text/html')
    for token in ['','family-role','device-inbox-token']:
        headers={'Authorization':'Bearer '+token}
        assert client.get('/api/fusion',headers=headers).status_code==401
        assert client.post('/api/fusion/binding',headers=headers,json={}).status_code==401
    assert client.get('/api/fusion',headers={'Origin':'https://device.example.invalid'}).status_code==403
    assert client.get('/fusion',headers={'Host':'pogo-plow-print.ngrok-free.dev'}).status_code==400
    normal=TestClient(create_broker_app(workflow,'operator',{'family':'family-role','bank':'bank-role'}),base_url='http://127.0.0.1:8766')
    assert normal.get('/fusion').status_code==404


def test_claimed_before_issue_survives_ambiguous_failure(demo):
    workflow, fusion, client, *rest=demo
    bind(workflow,client)
    with sqlite3.connect(rest[-1]) as db:
        record={'event':fusion.event('verify-1'),'status':'claimed','timeline':[],'reason':'uncertain'}
        db.execute('INSERT INTO fusion_events VALUES (?,?)',('verify-1',json.dumps(record)))
    assert process(client).json()['status']=='claimed'
    assert workflow.pending_confirmation() is None


def test_rejected_reviewer_response_does_not_invent_response_or_result(demo):
    from tests.test_contact_binding import sign
    workflow, fusion, client, family, bank, *_ = demo
    bind(workflow,client)
    record=process(client).json()
    # Authentic bank key cannot approve the family request.
    bundle={'request':workflow._pending[0]}
    response=client.post('/api/review/decision',headers={'Authorization':'Bearer family-role'},json={
        'decision':sign(bundle,bank).model_dump(), 'challenge_response':record['out_of_band_challenge']})
    assert response.status_code==409
    row=next(r for r in fusion.snapshot()['events'] if r['event']['event_id']=='verify-1')
    assert len(row['timeline'])==2 and row['status']=='request_created'
    assert workflow.status()['outcome'] is None


def test_consumed_event_keeps_original_binding_after_operator_rebind(demo):
    workflow, fusion, client, *_=demo
    bind(workflow,client)
    record=process(client).json()
    assert bind(workflow,client,claimed_identity='saved-bank',amount_cents=200).status_code==200
    again=process(client).json()
    assert again['request']['request_id']==record['request']['request_id']
    assert again['binding']['claimed_identity']=='saved-family'
    assert again['binding']['amount_cents']==100
    assert workflow.pending_confirmation()['operation']['amount_cents']==100


def test_new_transcript_invalidates_request_before_expiry_without_fabricated_response(demo):
    workflow, fusion, client, _, _, clock, *_ = demo
    bind(workflow,client)
    record=process(client).json()
    assert clock[0] < record['request']['expires_at']
    workflow.ingest(Transcript(segment_id='new-evidence',text='Send money.',start_ms=2,end_ms=3,final=True))
    context=workflow.binding_context()
    assert context['risk_state']=='CHALLENGED'
    assert context['pending'] is False
    assert context['authorization_denied'] is False
    row=next(r for r in fusion.snapshot()['events'] if r['event']['event_id']=='verify-1')
    assert row['status']=='no_longer_pending'
    assert len(row['timeline'])==2
