"""Real SDK envelopes captured in memory; no network or live databases."""
import json
import sqlite3

import pytest
from fastapi.testclient import TestClient

sentry_sdk = pytest.importorskip('sentry_sdk')
from sentry_sdk.transport import Transport
from sentry_sdk import logger
from callgate import reach_observability as telemetry
from callgate.device_events import create_app
from callgate.help_requests import HelpStore, HelpPrincipal
from callgate.help_transport import create_help_app


def test_canonical_cloud_routing_preserves_credentials_and_project():
    from urllib.parse import urlsplit
    bad = 'https://'+'a'*32+'@o123.ingest.us.sentry.io/extra/routing/prefix/path/456'
    fixed = telemetry.canonical_cloud_ingest_dsn(bad)
    before, after = urlsplit(bad), urlsplit(fixed)
    assert before.netloc == after.netloc
    assert before.scheme == after.scheme
    assert after.path == '/456'
    assert telemetry.canonical_cloud_ingest_dsn(fixed) == fixed
    with pytest.raises(ValueError):
        telemetry.canonical_cloud_ingest_dsn('https://'+'a'*32+'@private.example.invalid/prefix/456')


class Capture(Transport):
    def __init__(self):
        super().__init__()
        self.envelopes = []

    def capture_envelope(self, envelope):
        self.envelopes.append(envelope)


@pytest.fixture
def capture(monkeypatch):
    monkeypatch.setenv('CALLGATE_SENTRY_DSN', 'https://test@example.invalid/1')
    monkeypatch.setattr(telemetry, '_sdk', None)
    output = Capture()
    assert telemetry.configure_reach_sentry(transport=output)
    yield output
    sentry_sdk.get_client().close()
    telemetry._sdk = None


def items(output, kind):
    return [json.loads(item.get_bytes()) for envelope in output.envelopes
            for item in envelope.items if item.headers['type'] == kind]


def test_actual_trace_and_logs_cover_flow_without_private_data(tmp_path, capture):
    device_token = 'private-device-credential-' + 'd'*40
    event = 'private-alarm-identifier'
    device = 'private-device-identifier'
    actor = 'private-human-identity'
    role_tokens = {role: 'private-'+role+'-credential-'+'x'*40
                   for role in ('owner', 'contact', 'dashboard')}
    principals = {role_tokens[role]: HelpPrincipal(role, actor, (device,)) for role in role_tokens}
    source = tmp_path/'private-source.sqlite3'
    inbox = TestClient(create_app(device_tokens={device: device_token}, viewer_token='v'*40, db_path=str(source)))
    auth = lambda token: {'Authorization': 'Bearer '+token, 'Cookie': 'private-cookie',
                          'X-Forwarded-For': '192.0.2.123'}
    sentry_sdk.set_user({'email': 'private-person@example.invalid'})
    sentry_sdk.set_context('private', {'token': device_token})
    sentry_sdk.set_tag('private', event)
    sentry_sdk.set_attribute('private', actor)
    payload = {'event_id': event, 'device_id': device, 'event_type': 'help_request'}
    assert inbox.post('/api/device-events?private=query-secret', headers=auth(device_token), json=payload).status_code == 201
    assert inbox.post('/api/device-events', headers=auth(device_token), json=payload).status_code == 200
    assert inbox.post('/api/device-events', headers=auth(device_token), json={**payload, 'alert_type': 'private-alert'}).status_code == 422
    assert inbox.post('/api/device-events', json=payload).status_code == 401
    store = HelpStore(source, tmp_path/'private-help.sqlite3', {device: {'owner': actor, 'contact': actor}})
    with TestClient(create_help_app(store, principals)) as help_client:
        path = '/api/help-requests/'+event
        assert help_client.get(path, headers=auth(device_token)).status_code == 401
        assert help_client.post(path+'/responses', headers=auth(role_tokens['owner']), json={'action_id':'private-action','response':'accept'}).status_code == 403
        assert help_client.post(path+'/responses', headers=auth(role_tokens['contact']), json={'action_id':'private-action','response':'accept'}).status_code == 200
        assert help_client.get(path, headers=auth(role_tokens['dashboard'])).json()['status'] == 'accepted'
        assert help_client.get('/api/help-requests', headers=auth(role_tokens['dashboard'])).status_code == 200
    # Deliberately injected test exception: only the outcome may be exported.
    with pytest.raises(sqlite3.OperationalError):
        with telemetry.operation('help.persist'):
            raise sqlite3.OperationalError('private-sql-error '+device_token)
    logger.info('private-raw-log '+device_token)
    sentry_sdk.capture_exception(ValueError('private-exception '+actor))
    sentry_sdk.flush()
    transactions = items(capture, 'transaction')
    log_batches = items(capture, 'log')
    assert transactions and log_batches
    logs = [log for batch in log_batches for log in batch['items']]
    steps = {log['attributes']['reach.step']['value'] for log in logs}
    assert {'device.upload','device.persist','help.sync','help.persist','help.response','help.read','help.list'} <= steps
    assert any(log['attributes']['reach.outcome']['value'] == 'error' for log in logs)
    assert all(log['trace_id'] for log in logs)
    traces = {t['contexts']['trace']['trace_id'] for t in transactions}
    assert any(log['trace_id'] in traces for log in logs)
    assert any(span['description'] == 'device.persist' for t in transactions for span in t['spans'])
    assert any(span['description'] == 'help.persist' for t in transactions for span in t['spans'])
    exported = b'\n'.join(e.serialize() for e in capture.envelopes).decode()
    for private in [device_token, event, device, actor, *role_tokens.values(), 'private-cookie',
                    '192.0.2.123', 'query-secret', 'private-alert', str(tmp_path),
                    'private-person', 'private-sql-error', 'private-exception', 'private-raw-log']:
        assert private not in exported
    assert not items(capture, 'event')


def test_disabled_does_not_initialize(monkeypatch):
    monkeypatch.setattr(telemetry, '_sdk', None)
    monkeypatch.delenv('CALLGATE_SENTRY_DSN', raising=False)
    assert telemetry.configure_reach_sentry() is False
    with telemetry.operation('device.upload') as fields:
        fields['reach.http_status'] = 201
    assert telemetry._sdk is None


def test_invalid_configuration_omits_values(monkeypatch, capsys):
    monkeypatch.setattr(telemetry, '_sdk', None)
    monkeypatch.setenv('CALLGATE_SENTRY_DSN', 'private-invalid-dsn')
    assert telemetry.configure_reach_sentry() is False
    assert 'private-invalid-dsn' not in capsys.readouterr().out
