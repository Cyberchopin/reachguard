from concurrent.futures import ThreadPoolExecutor
import sqlite3
import threading

import pytest
from fastapi.testclient import TestClient
from callgate.device_events import create_app
from callgate.help_requests import HelpStore,HelpPrincipal
from callgate.help_transport import create_help_app

TOKENS={'owner':'o'*40,'contact':'c'*40,'dashboard':'v'*40,'other-owner':'x'*40,'other-contact':'y'*40}
PRINCIPALS={
    'owner':HelpPrincipal('owner','student',('nano-01',)),
    'contact':HelpPrincipal('contact','family',('nano-01',)),
    'dashboard':HelpPrincipal('dashboard','display',('nano-01',)),
    'other-owner':HelpPrincipal('owner','other-student',('nano-02',)),
    'other-contact':HelpPrincipal('contact','other-family',('nano-02',)),
}


def auth(role):return {'Authorization':'Bearer '+TOKENS.get(role,role)}


@pytest.fixture
def demo(tmp_path):
    source=tmp_path/'inbox.sqlite3';state=tmp_path/'help.sqlite3'
    device=TestClient(create_app(device_tokens={'nano-01':'d'*40,'nano-02':'e'*40},viewer_token='z'*40,db_path=str(source)))
    def upload(event_id='help-1',device_id='nano-01',kind='help_request'):
        return device.post('/api/device-events',headers={'Authorization':'Bearer '+('d'*40 if device_id=='nano-01' else 'e'*40)},json={'event_id':event_id,'device_id':device_id,'event_type':kind})
    upload();upload('help-2');upload('foreign','nano-02');upload('verify-only',kind='verify_request')
    routes={'nano-01':{'owner':'student','contact':'family'},'nano-02':{'owner':'other-student','contact':'other-family'}}
    store=HelpStore(source,state,routes)
    client=TestClient(create_help_app(store,{TOKENS[role]:p for role,p in PRINCIPALS.items()}))
    return store,client,upload,source,state,routes


def respond(client,action='a1',response='accept',event='help-1',role='contact'):
    return client.post(f'/api/help-requests/{event}/responses',headers=auth(role),json={'action_id':action,'response':response})


def cancel(client,action='cancel-1',event='help-1',role='owner'):
    return client.post(f'/api/help-requests/{event}/cancel',headers=auth(role),json={'action_id':action})


def test_independent_import_and_source_compatibility(demo):
    store,client,upload,source,*_=demo
    listing=client.get('/api/help-requests',headers=auth('owner')).json()
    assert {r['event_id'] for r in listing['requests']}=={'help-1','help-2'}
    assert all(r['status']=='recorded' and len(r['history'])==1 for r in listing['requests'])
    assert listing['notification_delivery_confirmed'] is False
    assert upload().status_code==200
    store.sync();store.sync()
    assert len(store.get('help-1',PRINCIPALS['owner'])['history'])==1
    assert client.get('/api/help-requests/verify-only',headers=auth('owner')).status_code==404
    with sqlite3.connect(source) as db:
        assert db.execute('SELECT count(*) FROM device_events').fetchone()[0]==4
    # New upload becomes a request with no policy/consent/amount/challenge steps.
    assert upload('new-help').status_code==201
    assert client.get('/api/help-requests/new-help',headers=auth('owner')).json()['status']=='recorded'


def test_contact_accept_cancel_history_and_duplicate_current_state(demo):
    _,client,*_=demo
    accepted=respond(client);assert accepted.status_code==200
    assert accepted.json()['request']['status']=='accepted'
    assert accepted.json()['request']['history'][-1]['actor_role']=='contact'
    assert respond(client).json()['duplicate'] is True
    assert respond(client,'a2').status_code==409
    assert respond(client,'a3','unable').status_code==409
    assert cancel(client).json()['request']['status']=='cancelled'
    repeated=respond(client)
    assert repeated.status_code==200 and repeated.json()['duplicate']
    assert repeated.json()['action']['after_state']=='accepted'
    assert repeated.json()['request']['status']=='cancelled' # Retry cannot resurrect acceptance.
    assert cancel(client).json()['duplicate'] is True
    assert cancel(client,'cancel-2').status_code==409
    history=client.get('/api/help-requests/help-1',headers=auth('owner')).json()['history']
    assert [h['result'] for h in history]==['applied','applied','rejected','rejected','applied','rejected']


def test_unable_and_cancel_are_distinct_actual_states(demo):
    _,client,*_=demo
    row=respond(client,response='unable').json()['request']
    assert row['status']=='unable_to_help'
    assert respond(client,'different-accept').status_code==409
    assert cancel(client).json()['request']['status']=='cancelled'
    assert [r['after_state'] for r in store_history(client) if r['result']=='applied']==['recorded','unable_to_help','cancelled']


def store_history(client):
    return client.get('/api/help-requests/help-1',headers=auth('owner')).json()['history']


def test_action_id_conflict_preserves_original(demo):
    _,client,*_=demo
    respond(client)
    assert respond(client,response='unable').status_code==409
    assert respond(client,event='help-2').status_code==409
    assert client.get('/api/help-requests/help-2',headers=auth('owner')).json()['status']=='recorded'
    assert len(store_history(client))==2


@pytest.mark.parametrize('role',['d'*40,'z'*40,'wrong',''])
def test_device_and_unknown_credentials_cannot_read_or_respond(demo,role):
    _,client,*_=demo
    assert client.get('/api/help-requests',headers=auth(role)).status_code==401
    assert respond(client,role=role).status_code==401
    assert cancel(client,role=role).status_code==401


def test_roles_and_scopes_are_separate(demo):
    _,client,*_=demo
    for role in ['owner','dashboard']:
        assert respond(client,role=role).status_code==403
    for role in ['contact','dashboard']:
        assert cancel(client,role=role).status_code==403
    for role in ['other-owner','other-contact']:
        assert client.get('/api/help-requests/help-1',headers=auth(role)).status_code==404
    assert respond(client,role='other-contact').status_code==404
    assert cancel(client,role='other-owner').status_code==404
    # Same device but wrong configured person still cannot enumerate or act.
    wrong=HelpPrincipal('contact','not-family',('nano-01',))
    store=demo[0]
    assert store.list(wrong)==[]
    with pytest.raises(ValueError):store.get('help-1',wrong)


def test_cancel_then_accept_rejection_is_audited_and_idempotent(demo):
    _,client,*_=demo
    assert cancel(client).status_code==200
    rejected=respond(client);assert rejected.status_code==409
    assert respond(client).json()['duplicate'] is True
    history=store_history(client)
    assert len(history)==3
    assert history[-1]['result']=='rejected' and history[-1]['after_state']=='cancelled'


def test_restart_keeps_requests_roles_and_idempotency(demo):
    store,client,_,source,state,routes=demo
    respond(client)
    again=HelpStore(source,state,routes)
    assert again.get('help-1',PRINCIPALS['owner'])['status']=='accepted'
    code,result=again.act('help-1','a1',PRINCIPALS['contact'],'accept')
    assert code==200 and result['duplicate']
    assert len(result['request']['history'])==2


def test_concurrent_same_response_creates_one_applied_audit(demo):
    store,*_=demo
    with ThreadPoolExecutor(max_workers=8) as pool:
        results=list(pool.map(lambda _:store.act('help-1','same',PRINCIPALS['contact'],'accept'),range(16)))
    assert all(code==200 for code,_ in results)
    assert sum(not result['duplicate'] for _,result in results)==1
    assert len(store.get('help-1',PRINCIPALS['owner'])['history'])==2


def test_two_contacts_with_new_action_ids_do_not_overwrite(demo):
    store,*_=demo
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(lambda command:store.act('help-1',command,PRINCIPALS['contact'],command),['accept','unable']))
    assert sorted(code for code,_ in results)==[200,409]
    row=store.get('help-1',PRINCIPALS['owner'])
    assert row['status'] in {'accepted','unable_to_help'}
    assert [h['result'] for h in row['history']]==['applied','applied','rejected']


def test_accept_cancel_race_is_serialized_and_finally_cancelled(demo):
    store,*_=demo
    barrier=threading.Barrier(2)
    def run(command):
        barrier.wait()
        return store.act('help-1',command,PRINCIPALS['owner' if command=='cancel' else 'contact'],command)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(run,['accept','cancel']))
    assert results[1][0]==200
    assert results[0][0] in {200,409}
    row=store.get('help-1',PRINCIPALS['owner'])
    assert row['status']=='cancelled' and len(row['history'])==3
    assert {h['command'] for h in row['history']}=={'record','accept','cancel'}
    assert all(h['actor_role']!='device' for h in row['history'][1:])


def test_strict_schema_cors_and_no_payment_or_config_routes(demo):
    _,client,*_=demo
    assert respond(client,response='approve_payment').status_code==422
    assert client.post('/api/help-requests/help-1/responses',headers=auth('contact'),json={'action_id':'x','response':'accept','amount':100}).status_code==422
    assert client.post('/api/help-requests/help-1/cancel',headers=auth('owner'),content='x'*2049).status_code==413
    assert client.get('/api/help-requests',headers={**auth('owner'),'Origin':'https://evil.example'}).status_code==403
    for path in ['/api/config','/api/credentials','/api/request','/api/review/pending','/fusion','/docs','/openapi.json','/.env']:
        assert client.get(path).status_code==404
