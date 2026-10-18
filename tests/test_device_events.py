from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient

from callgate.device_events import create_app

TOKENS = {"nano-01": "a" * 32, "nano-02": "b" * 32}
VIEWER = "v" * 32
EVENT = {"event_id": "evt-1", "device_id": "nano-01", "event_type": "verify_request"}


def auth(token="a" * 32):
    return {"Authorization": "Bearer " + token}


@pytest.fixture
def inbox(tmp_path):
    path = str(tmp_path / "events.sqlite3")
    def client():
        return TestClient(create_app(device_tokens=TOKENS, viewer_token=VIEWER, db_path=path))
    return client


def test_persistent_idempotency_and_conflicts(inbox):
    client = inbox()
    first = client.post('/api/device-events', json=EVENT, headers=auth())
    assert first.status_code == 201
    again = inbox().post('/api/device-events', json=EVENT, headers=auth())
    assert again.status_code == 200
    assert first.json()['event'] == again.json()['event']
    assert again.json()['intent_only'] is True
    assert client.post('/api/device-events', json={**EVENT, 'event_type':'help_request'}, headers=auth()).status_code == 409
    assert client.post('/api/device-events', json={**EVENT, 'device_id':'nano-02'}, headers=auth(TOKENS['nano-02'])).status_code == 409


def test_auth_and_route_isolation(inbox):
    client = inbox()
    for token in ['', VIEWER, 'wrong', 'é']:
        headers = auth(token) if token != 'é' else {}
        assert client.post('/api/device-events', json=EVENT, headers=headers).status_code == 401
    assert client.post('/api/device-events', json=EVENT, headers=auth(TOKENS['nano-02'])).status_code == 403
    assert client.get('/api/device-events', headers=auth()).status_code == 401
    assert client.get('/api/device-events', headers=auth(VIEWER)).json()['events'] == []
    assert client.get('/').status_code == 200
    for route in ['/docs', '/openapi.json', '/api/approve', '/participant', '/reviewer']:
        assert client.get(route).status_code == 404


@pytest.mark.parametrize('change', [{'event_type':'payment_approved'}, {'amount':1}, {'event_id':''}, {'event_id':1}, {'device_id':'<script>'}])
def test_strict_schema(inbox, change):
    r = inbox().post('/api/device-events', json={**EVENT, **change}, headers=auth())
    assert r.status_code == 422
    assert 'input' not in r.text


def test_help_and_bounded_body(inbox):
    client = inbox()
    assert client.post('/api/device-events', json={**EVENT,'event_type':'help_request'}, headers=auth()).status_code == 201
    assert client.post('/api/device-events', content='x'*2049, headers=auth()).status_code == 413
    assert client.post('/api/device-events', content='{', headers=auth()).status_code == 422
    assert len(client.get('/api/device-events', headers=auth(VIEWER)).json()['events']) == 1


def test_concurrent_retries(inbox):
    client = inbox()
    with ThreadPoolExecutor(max_workers=8) as pool:
        codes = list(pool.map(lambda _: client.post('/api/device-events', json=EVENT, headers=auth()).status_code, range(12)))
    assert codes.count(201) == 1
    assert codes.count(200) == 11


def test_fail_closed(tmp_path):
    with pytest.raises(ValueError):
        create_app(device_tokens=TOKENS, viewer_token=TOKENS['nano-01'], db_path=str(tmp_path/'db'))
