from datetime import datetime, timedelta, timezone
import sqlite3

import pytest
from fastapi.testclient import TestClient
from callgate.device_events import create_app
from callgate.help_requests import HelpStore,HelpPrincipal
from callgate.help_transport import create_help_app

TOKENS={'owner':'o'*40,'c1':'1'*40,'c2':'2'*40,'c3':'3'*40,'dashboard':'v'*40}
PRINCIPALS={
    'owner':HelpPrincipal('owner','student',('nano-01',)),
    'c1':HelpPrincipal('contact','daughter',('nano-01',)),
    'c2':HelpPrincipal('contact','son',('nano-01',)),
    'c3':HelpPrincipal('contact','neighbour',('nano-01',)),
    'dashboard':HelpPrincipal('dashboard','display',('nano-01',)),
}
ROUTES={'nano-01':{'owner':'student','contact':'daughter','contacts':['daughter','son','neighbour']}}


class Clock:
    def __init__(self):self.t=datetime(2026,10,18,9,0,tzinfo=timezone.utc)
    def __call__(self):return self.t
    def advance(self,seconds):self.t+=timedelta(seconds=seconds)


def auth(role):return {'Authorization':'Bearer '+TOKENS[role]}


@pytest.fixture
def demo(tmp_path):
    source=tmp_path/'inbox.sqlite3';state=tmp_path/'help.sqlite3';clock=Clock()
    device=TestClient(create_app(device_tokens={'nano-01':'d'*40},viewer_token='z'*40,db_path=str(source)))
    def upload(event_id='help-1'):
        return device.post('/api/device-events',headers={'Authorization':'Bearer '+'d'*40},json={'event_id':event_id,'device_id':'nano-01','event_type':'help_request'})
    upload()
    store=HelpStore(source,state,ROUTES,wait_seconds=20,now=clock)
    client=TestClient(create_help_app(store,{TOKENS[role]:p for role,p in PRINCIPALS.items()}))
    return store,client,clock,upload,source,state


def respond(client,role,action='a1',response='accept',event='help-1'):
    return client.post(f'/api/help-requests/{event}/responses',headers=auth(role),json={'action_id':action,'response':response})


def visible(client,role):
    return [r['event_id'] for r in client.get('/api/help-requests',headers=auth(role)).json()['requests']]


def notified(store):
    row=store.get('help-1',PRINCIPALS['owner'])
    return [(h['command'],h['actor_id']) for h in row['history'] if h['command'] in ('notify','timeout')]


def test_first_contact_is_notified_at_once_and_only_they_see_it(demo):
    store,client,*_=demo
    row=store.get('help-1',PRINCIPALS['owner'])
    assert row['status']=='recorded'
    assert row['rotation']['current_contact']=='daughter' and row['rotation']['round']==1
    assert notified(store)==[('notify','daughter')]
    assert visible(client,'c1')==['help-1'] and visible(client,'c2')==[] and visible(client,'c3')==[]
    assert respond(client,'c2').status_code==404


def test_rotation_moves_on_after_the_wait_and_wraps_to_a_new_round(demo):
    store,client,clock,*_=demo
    clock.advance(19);store.sync()
    assert notified(store)==[('notify','daughter')]
    clock.advance(1);store.sync()
    assert notified(store)==[('notify','daughter'),('timeout','daughter'),('notify','son')]
    assert visible(client,'c2')==['help-1'] and visible(client,'c3')==[]
    clock.advance(20);store.sync()
    clock.advance(20);store.sync()
    row=store.get('help-1',PRINCIPALS['owner'])
    assert row['rotation']['current_contact']=='daughter' and row['rotation']['round']==2
    assert [c for c,_ in notified(store)].count('notify')==4
    assert row['status']=='recorded'


def test_accept_stops_rotation(demo):
    store,client,clock,*_=demo
    clock.advance(20);store.sync()
    assert respond(client,'c2').json()['request']['status']=='accepted'
    clock.advance(200);store.sync()
    assert notified(store)==[('notify','daughter'),('timeout','daughter'),('notify','son')]
    assert visible(client,'c3')==[]


def test_earlier_contact_can_still_accept_after_rotation_moved_on(demo):
    store,client,clock,*_=demo
    clock.advance(20);store.sync()
    accepted=respond(client,'c1')
    assert accepted.status_code==200 and accepted.json()['request']['status']=='accepted'
    assert respond(client,'c2','a2').status_code==409


def test_owner_cancel_stops_rotation(demo):
    store,client,clock,*_=demo
    cancelled=client.post('/api/help-requests/help-1/cancel',headers=auth('owner'),json={'action_id':'cancel-1'})
    assert cancelled.json()['request']['status']=='cancelled'
    clock.advance(200);store.sync()
    assert notified(store)==[('notify','daughter')]
    assert respond(client,'c1').status_code==409


def test_unable_keeps_its_existing_meaning(demo):
    store,client,clock,*_=demo
    assert respond(client,'c1',response='unable').json()['request']['status']=='unable_to_help'
    clock.advance(200);store.sync()
    assert notified(store)==[('notify','daughter')]


def test_restart_resumes_where_it_stopped_without_replaying(demo):
    store,client,clock,upload,source,state=demo
    clock.advance(20);store.sync()
    clock.advance(600)  # service down for ten minutes
    again=HelpStore(source,state,ROUTES,wait_seconds=20,now=clock)
    assert notified(again)==[('notify','daughter'),('timeout','daughter'),('notify','son'),('timeout','son'),('notify','neighbour')]
    again.sync()
    assert len(notified(again))==5


def test_requests_recorded_before_rotation_keep_single_contact(tmp_path):
    source=tmp_path/'inbox.sqlite3';state=tmp_path/'help.sqlite3';clock=Clock()
    device=TestClient(create_app(device_tokens={'nano-01':'d'*40},viewer_token='z'*40,db_path=str(source)))
    post=lambda e:device.post('/api/device-events',headers={'Authorization':'Bearer '+'d'*40},json={'event_id':e,'device_id':'nano-01','event_type':'help_request'})
    post('old')
    HelpStore(source,state,{'nano-01':{'owner':'student','contact':'daughter'}},now=clock)
    post('new')
    store=HelpStore(source,state,ROUTES,wait_seconds=20,now=clock)
    assert store.get('old',PRINCIPALS['owner'])['rotation'] is None
    assert store.get('new',PRINCIPALS['owner'])['rotation']['current_contact']=='daughter'
    clock.advance(200);store.sync()
    assert len(store.get('old',PRINCIPALS['owner'])['history'])==1


def test_concurrent_rotation_passes_step_once(demo):
    store,_,clock,*_=demo
    clock.advance(20)
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(lambda _:store.sync(),range(8)))
    assert notified(store)==[('notify','daughter'),('timeout','daughter'),('notify','son')]


@pytest.mark.parametrize('route',[
    {'owner':'s','contact':'a','contacts':['b','a']},
    {'owner':'s','contact':'a','contacts':['a','']},
    {'owner':'s','contact':'a','contacts':[]},
    {'owner':'s','contact':'a','extra':'x'},
])
def test_invalid_rotation_routes_are_refused(tmp_path,route):
    source=tmp_path/'inbox.sqlite3'
    create_app(device_tokens={'nano-01':'d'*40},viewer_token='z'*40,db_path=str(source))
    with pytest.raises(ValueError):
        HelpStore(source,tmp_path/'help.sqlite3',{'nano-01':route})


def test_schedule_with_repeats_alternates_family_then_others(tmp_path):
    from scripts.start_help_demo import rotation_schedule
    schedule=rotation_schedule(['daughter','son','neighbour','carer'],level1=2,attempts=3)
    assert schedule==['daughter','son','daughter','son','daughter','son','neighbour','carer']
    assert rotation_schedule(['a','b','c'])==['a','b','c']
    for bad in [dict(level1=0),dict(level1=4),dict(attempts=0)]:
        with pytest.raises(ValueError):rotation_schedule(['a','b','c'],**bad)
    source=tmp_path/'inbox.sqlite3';clock=Clock()
    device=TestClient(create_app(device_tokens={'nano-01':'d'*40},viewer_token='z'*40,db_path=str(source)))
    device.post('/api/device-events',headers={'Authorization':'Bearer '+'d'*40},json={'event_id':'help-1','device_id':'nano-01','event_type':'help_request'})
    store=HelpStore(source,tmp_path/'help.sqlite3',{'nano-01':{'owner':'student','contact':'daughter','contacts':schedule}},wait_seconds=20,now=clock)
    for _ in range(8):
        clock.advance(20);store.sync()
    row=store.get('help-1',PRINCIPALS['owner'])
    assert [h['actor_id'] for h in row['history'] if h['command']=='notify']==schedule+['daughter']
    assert row['rotation']['round']==2
    # A repeated contact is still one contact: they see the request once and can accept it.
    assert [r['event_id'] for r in store.list(PRINCIPALS['c1'])]==['help-1']
    assert store.act('help-1','a1',PRINCIPALS['c1'],'accept')[1]['request']['status']=='accepted'
