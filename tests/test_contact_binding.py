"""Trusted enrollment boundaries, not a claim of independent human identity."""
import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from callgate.contacts import ContactDirectory, SavedContact
from callgate.confirmation import ConfirmationCoordinator, ReviewerDecision, decision_bytes
from callgate.models import Transcript
from callgate.verification import DemoVerificationGate
from callgate.workflow import DemoWorkflow


def setup(origin='recipient-device', contact_origin='family-device'):
    issuer, family, other = [Ed25519PrivateKey.generate() for _ in range(3)]
    directory = ContactDirectory([
        SavedContact(identity='saved-family', reviewer='family', credential_origin=contact_origin),
        SavedContact(identity='saved-bank', reviewer='bank', credential_origin='bank-device'),
    ])
    clock = [1000]
    coordinator = ConfirmationCoordinator('issuer', issuer,
        {'family': family.public_key(), 'bank': other.public_key()}, clock=lambda: clock[0],
        contacts=directory, initiator_origin=origin)
    workflow = DemoWorkflow(coordinator, DemoVerificationGate({'issuer': issuer.public_key()},
        clock=lambda: clock[0]), None)
    workflow.set_processing_consent(True)
    workflow.ingest(Transcript(segment_id='s', text='Send money.', start_ms=0, end_ms=1, final=True))
    return workflow, family, other, clock


def request(workflow, identity='saved-family', amount=100):
    return workflow.request_confirmation(destination='fictional-wallet', amount_cents=amount,
        claimed_identity=identity)


def sign(bundle, key, approved=True, changes=None):
    req = bundle['request']
    if changes:
        req = req.model_copy(update=changes)
    return ReviewerDecision(request=req, approved=approved,
        signature=key.sign(decision_bytes(req, approved)).hex())


def test_saved_identity_selects_registered_key_and_binds_operation():
    workflow, family, _, _ = setup()
    bundle = request(workflow)
    assert bundle['request'].reviewer == 'family'
    assert bundle['request'].claimed_identity == 'saved-family'
    assert bundle['operation']['claimed_identity'] == 'saved-family'
    result = workflow.complete(sign(bundle, family), challenge_response=bundle['out_of_band_challenge'])
    assert result['status'] == 'simulated_action_completed'
    with pytest.raises(ValueError):
        workflow.complete(sign(bundle, family), challenge_response=bundle['out_of_band_challenge'])


@pytest.mark.parametrize('identity', [None, '', 'unknown-family'])
def test_no_fallback_for_missing_or_unknown_identity(identity):
    workflow, _, _, _ = setup()
    with pytest.raises(ValueError):
        request(workflow, identity)
    assert workflow.pending_confirmation() is None


def test_same_credential_origin_cannot_self_approve():
    workflow, _, _, _ = setup(contact_origin='recipient-device')
    with pytest.raises(ValueError, match='self-approval'):
        request(workflow)


def test_wrong_saved_contact_key_rejected_without_consuming_valid_request():
    workflow, family, other, _ = setup()
    bundle = request(workflow)
    with pytest.raises(ValueError, match='signature'):
        workflow.complete(sign(bundle, other), challenge_response=bundle['out_of_band_challenge'])
    assert workflow.complete(sign(bundle, family), challenge_response=bundle['out_of_band_challenge'])


@pytest.mark.parametrize('changes', [
    {'session_id': 'other-session'}, {'resource': 'other-destination-or-amount'},
    {'claimed_identity': 'saved-bank'}, {'reviewer': 'bank'}, {'request_id': 'a'*64},
])
def test_even_registered_signer_cannot_change_scope(changes):
    workflow, family, _, _ = setup()
    bundle = request(workflow)
    with pytest.raises(ValueError):
        workflow.complete(sign(bundle, family, changes=changes),
            challenge_response=bundle['out_of_band_challenge'])


@pytest.mark.parametrize('terminal', ['denied', 'expired'])
def test_denial_and_expiry_survive_identity_and_amount_changes(terminal):
    workflow, family, _, clock = setup()
    bundle = request(workflow)
    if terminal == 'denied':
        workflow.complete(sign(bundle, family, False))
    else:
        clock[0] = bundle['request'].expires_at
        with pytest.raises(ValueError):
            workflow.complete(sign(bundle, family), challenge_response=bundle['out_of_band_challenge'])
    with pytest.raises(ValueError, match='denied'):
        request(workflow, 'saved-bank', 200)


def test_duplicate_identity_rejected_at_provisioning():
    contact = SavedContact(identity='same', reviewer='family', credential_origin='family-device')
    with pytest.raises(ValueError, match='duplicate'):
        ContactDirectory([contact, contact])


def test_same_key_cannot_be_enrolled_for_different_reviewers():
    key, issuer = Ed25519PrivateKey.generate(), Ed25519PrivateKey.generate()
    directory = ContactDirectory([
        SavedContact(identity='a', reviewer='first', credential_origin='first-origin'),
        SavedContact(identity='b', reviewer='second', credential_origin='second-origin')])
    with pytest.raises(ValueError, match='shared'):
        ConfirmationCoordinator('issuer', issuer, {'first':key.public_key(), 'second':key.public_key()},
            contacts=directory, initiator_origin='recipient-device')


def test_old_decision_cannot_authorize_changed_amount():
    workflow, family, _, _ = setup()
    old = request(workflow)
    new = request(workflow, amount=200)
    assert old['request'].resource != new['request'].resource
    with pytest.raises(ValueError):
        workflow.complete(sign(old, family), challenge_response=old['out_of_band_challenge'])
    assert workflow.complete(sign(new, family), challenge_response=new['out_of_band_challenge'])


def test_reviewer_surface_rejects_other_addressee_and_identity_mismatch():
    from fastapi.testclient import TestClient
    from callgate.review_transport import create_reviewer_app
    workflow, family, _, _ = setup()
    bundle = request(workflow)
    view = workflow.pending_confirmation()
    app = create_reviewer_app(family, 'test-reviewer-token', lambda: view,
        lambda submission: None, expected_reviewer='family')
    with TestClient(app, base_url='http://127.0.0.1:8767') as client:
        headers = {'Authorization': 'Bearer test-reviewer-token'}
        assert client.get('/api/pending', headers=headers).status_code == 200
        view['request']['reviewer'] = 'bank'
        assert client.get('/api/pending', headers=headers).status_code == 409
        view['request']['reviewer'] = 'family'
        view['request']['claimed_identity'] = 'saved-bank'
        assert client.get('/api/pending', headers=headers).status_code == 409


def test_status_observes_timeout_and_explains_session_denial():
    workflow, _, _, clock = setup()
    bundle = request(workflow)
    clock[0] = bundle['request'].expires_at
    status = workflow.status()
    assert status['pending'] is False
    assert status['authorization_denied'] is True
    assert workflow.pending_confirmation() is None


def test_broker_reviewer_capability_cannot_read_or_submit_another_contact_request():
    from fastapi.testclient import TestClient
    from callgate.review_transport import create_broker_app
    workflow, _, bank, _ = setup()
    with pytest.raises(ValueError, match='route'):
        create_broker_app(workflow, 'participant-token', 'family-token')
    app = create_broker_app(workflow, 'participant-token', 'family-token', reviewer_identity='family')
    bundle = request(workflow, 'saved-bank')
    with TestClient(app, base_url='http://127.0.0.1:8766') as client:
        headers = {'Authorization': 'Bearer family-token'}
        assert client.get('/api/review/pending', headers=headers).json() is None
        response = client.post('/api/review/decision', headers=headers, json={
            'decision': sign(bundle, bank).model_dump(),
            'challenge_response': bundle['out_of_band_challenge']})
        assert response.status_code == 409
    assert workflow.status()['outcome'] is None
