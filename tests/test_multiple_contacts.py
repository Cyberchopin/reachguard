"""Multiple reviewer capabilities must preserve claimed-identity routing."""
import pytest
from fastapi.testclient import TestClient
from callgate.review_transport import create_broker_app
from scripts.start_review_demo import _contact_ids
from tests.test_contact_binding import setup, request, sign


def test_each_reviewer_can_only_read_and_submit_its_own_request():
    workflow, family, bank, _ = setup()
    app = create_broker_app(workflow, 'participant-token',
        {'family': 'family-token', 'bank': 'bank-token'})
    with TestClient(app, base_url='http://127.0.0.1:8766') as client:
        bundle = request(workflow, 'saved-bank')
        family_headers = {'Authorization':'Bearer family-token'}
        bank_headers = {'Authorization':'Bearer bank-token'}
        assert client.get('/api/review/pending', headers=family_headers).json() is None
        assert client.get('/api/review/pending', headers=bank_headers).json()['request']['reviewer'] == 'bank'
        payload = {'decision':sign(bundle, bank).model_dump(),
                   'challenge_response':bundle['out_of_band_challenge']}
        assert client.post('/api/review/decision', headers=family_headers, json=payload).status_code == 409
        assert workflow.status()['outcome'] is None
        assert client.post('/api/review/decision', headers=bank_headers, json=payload).json()['status'] == 'simulated_action_completed'
        assert client.post('/api/review/decision', headers=bank_headers, json=payload).status_code == 409


@pytest.mark.parametrize('tokens', [
    {}, {'family':''}, {'family':'same','bank':'same'}, {'family':'participant-token'},
    {'family':None}, {'':'family-token'},
    {None:'unscoped-token'},
])
def test_ambiguous_or_overlapping_capabilities_rejected_at_startup(tokens):
    workflow, _, _, _ = setup()
    with pytest.raises(ValueError):
        create_broker_app(workflow, 'participant-token', tokens)


def test_switch_identity_hides_superseded_request_and_invalidates_old_signature():
    workflow, family, bank, _ = setup()
    app = create_broker_app(workflow, 'participant-token',
        {'family':'family-token', 'bank':'bank-token'})
    old = request(workflow, 'saved-family')
    new = request(workflow, 'saved-bank')
    with TestClient(app, base_url='http://127.0.0.1:8766') as client:
        assert client.get('/api/review/pending', headers={'Authorization':'Bearer family-token'}).json() is None
        assert client.post('/api/review/decision', headers={'Authorization':'Bearer family-token'},
            json={'decision':sign(old, family).model_dump(),
                  'challenge_response':old['out_of_band_challenge']}).status_code == 409
        assert client.post('/api/review/decision', headers={'Authorization':'Bearer bank-token'},
            json={'decision':sign(new, bank).model_dump(),
                  'challenge_response':new['out_of_band_challenge']}).status_code == 200


@pytest.mark.parametrize('ids', [['same','same'], ['bad identity'], ['a','b','c','d','e']])
def test_invalid_launcher_directory_fails_before_process_start(ids):
    with pytest.raises(ValueError):
        _contact_ids(ids)


def test_default_and_multiple_contact_cli_configuration():
    assert _contact_ids(None) == ['saved-family']
    assert _contact_ids(['family','bank']) == ['family','bank']


def test_participant_and_unknown_capabilities_cannot_access_reviewer_routes():
    workflow, _, _, _ = setup()
    app = create_broker_app(workflow, 'participant-token', {'family':'family-token','bank':'bank-token'})
    request(workflow)
    with TestClient(app, base_url='http://127.0.0.1:8766') as client:
        for token in ['participant-token', 'unknown-token']:
            assert client.get('/api/review/pending',
                headers={'Authorization':'Bearer '+token}).status_code == 401
