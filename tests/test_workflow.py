import pytest
pytest.importorskip('cryptography')
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from callgate.confirmation import ConfirmationCoordinator, ReviewerDecision, decision_bytes
from callgate.verification import DemoVerificationGate
from callgate.workflow import DemoWorkflow
from callgate.models import Transcript


def setup():
    issuer, reviewer = Ed25519PrivateKey.generate(), Ed25519PrivateKey.generate()
    clock = [1000]
    coordinator = ConfirmationCoordinator('issuer', issuer, {'reviewer': reviewer.public_key()},
                                           clock=lambda: clock[0])
    gate = DemoVerificationGate({'issuer': issuer.public_key()}, clock=lambda: clock[0])
    workflow = DemoWorkflow(coordinator, gate, 'reviewer', request_clock=lambda: clock[0])
    workflow.set_processing_consent(True)
    workflow.ingest(Transcript(segment_id='s', text='Move your savings into the secure holding wallet.',
                               final=True, start_ms=0, end_ms=1000))
    bundle = workflow.request_confirmation(destination='demo-wallet', amount_cents=280000)
    return workflow, reviewer, bundle, clock


def sign(key, bundle, approved=True):
    request = bundle['request']
    return ReviewerDecision(request=request, approved=approved,
        signature=key.sign(decision_bytes(request, approved)).hex())


def test_complete_once():
    workflow, reviewer, bundle, _ = setup()
    decision = sign(reviewer, bundle)
    result = workflow.complete(decision, challenge_response=bundle['out_of_band_challenge'])
    assert result['status'] == 'simulated_action_completed'
    assert result['operation']['amount_cents'] == 280000
    assert result['real_action_executed'] is False
    with pytest.raises(ValueError):
        workflow.complete(decision, challenge_response=bundle['out_of_band_challenge'])


def test_forged_and_expired_confirmation():
    workflow, reviewer, bundle, clock = setup()
    with pytest.raises(ValueError, match='signature'):
        workflow.complete(sign(Ed25519PrivateKey.generate(), bundle),
                          challenge_response=bundle['out_of_band_challenge'])
    clock[0] += 121
    with pytest.raises(ValueError, match='expired'):
        workflow.complete(sign(reviewer, bundle),
                          challenge_response=bundle['out_of_band_challenge'])


def test_new_evidence_invalidates_and_secrecy_blocks():
    workflow, reviewer, bundle, _ = setup()
    workflow.ingest(Transcript(segment_id='s2', text='Do not tell anyone.', final=True,
                               start_ms=1000, end_ms=2000))
    with pytest.raises(ValueError):
        workflow.complete(sign(reviewer, bundle),
                          challenge_response=bundle['out_of_band_challenge'])
    with pytest.raises(ValueError, match='policy'):
        workflow.request_confirmation(destination='demo-wallet', amount_cents=280000)


def test_denial_and_cross_session():
    workflow, reviewer, bundle, _ = setup()
    other, _, _, _ = setup()
    with pytest.raises(ValueError):
        other.complete(sign(reviewer, bundle))
    assert workflow.complete(sign(reviewer, bundle, False))['status'] == 'reviewer_denied'


def test_denied_operation_cannot_get_a_new_challenge_in_same_session():
    workflow, reviewer, bundle, _ = setup()
    workflow.complete(sign(reviewer, bundle, False))
    with pytest.raises(ValueError, match='denied'):
        workflow.request_confirmation(destination='demo-wallet', amount_cents=280000)
    # Changing transcript revisions cannot clear the denial record.
    workflow.ingest(Transcript(segment_id='s2', text='Please send money.',
                               final=True, start_ms=1000, end_ms=2000))
    with pytest.raises(ValueError, match='denied'):
        workflow.request_confirmation(destination='demo-wallet', amount_cents=280000)


def test_superseded_requests_do_not_exhaust_pending_capacity():
    workflow, reviewer, bundle, clock = setup()
    old = sign(reviewer, bundle)
    for _ in range(1001):
        clock[0] += 121
        # Timeout now revokes the session. Capacity regression uses explicit
        # independent sessions, not silent renewal of an expired authorization.
        workflow.reset_session()
        workflow.set_processing_consent(True)
        workflow.ingest(Transcript(segment_id='s', text='Send money.', final=True,
                                   start_ms=0, end_ms=1000))
        bundle = workflow.request_confirmation(destination='demo-wallet', amount_cents=280000)
    with pytest.raises(ValueError):
        workflow.complete(old, challenge_response='000000')
    assert workflow.complete(sign(reviewer, bundle),
        challenge_response=bundle['out_of_band_challenge'])['status'] == 'simulated_action_completed'


def test_approval_requires_challenge_and_three_failures_cancel_request():
    workflow, reviewer, bundle, _ = setup()
    decision = sign(reviewer, bundle)
    wrong = '000000' if bundle['out_of_band_challenge'] != '000000' else '111111'
    for _ in range(2):
        with pytest.raises(ValueError, match='challenge'):
            workflow.complete(decision, challenge_response=wrong)
        assert workflow.status()['pending'] is True
    with pytest.raises(ValueError, match='challenge'):
        workflow.complete(decision, challenge_response=wrong)
    assert workflow.status()['pending'] is False


def test_processing_requires_consent_and_withdrawal_clears_session():
    issuer, reviewer = Ed25519PrivateKey.generate(), Ed25519PrivateKey.generate()
    coordinator = ConfirmationCoordinator('issuer', issuer, {'reviewer': reviewer.public_key()})
    gate = DemoVerificationGate({'issuer': issuer.public_key()})
    workflow = DemoWorkflow(coordinator, gate, 'reviewer')
    segment = Transcript(segment_id='s', text='Send money right now.', final=True,
                         start_ms=0, end_ms=1000)
    with pytest.raises(ValueError, match='consent'):
        workflow.ingest(segment)
    assert workflow.set_processing_consent(True)['processing_allowed'] is True
    workflow.ingest(segment)
    workflow.request_confirmation(destination='demo-wallet', amount_cents=100)
    result = workflow.set_processing_consent(False)
    assert result == {'processing_consent': 'REVOKED', 'processing_allowed': False}
    assert workflow.status()['risk_state'] == 'UNVERIFIED'
    assert workflow.status()['pending'] is False
    assert workflow.pending_confirmation() is None
    with pytest.raises(ValueError, match='consent'):
        workflow.ingest(segment)


def test_new_session_invalidates_old_confirmation_and_requires_fresh_consent():
    workflow, reviewer, bundle, _ = setup()
    old_decision = sign(reviewer, bundle)
    reset = workflow.reset_session()
    assert reset['risk_state'] == 'UNVERIFIED'
    assert reset['processing_consent'] == 'NOT_REQUESTED'
    with pytest.raises(ValueError):
        workflow.complete(old_decision,
                          challenge_response=bundle['out_of_band_challenge'])
    with pytest.raises(ValueError, match='consent'):
        workflow.ingest(Transcript(segment_id='new', text='Hello', final=True,
                                   start_ms=0, end_ms=1000))


@pytest.mark.parametrize('change', ['reset', 'withdraw'])
def test_late_audio_cannot_enter_reconsented_session(change):
    workflow, _, _, _ = setup()
    generation = workflow.processing_generation()
    if change == 'reset':
        workflow.reset_session()
    else:
        workflow.set_processing_consent(False)
    workflow.set_processing_consent(True)
    with pytest.raises(ValueError, match='stale'):
        workflow.ingest(Transcript(segment_id='late', text='Send money.',
            start_ms=0, end_ms=1000, final=True), generation=generation)
    assert workflow.status()['risk_state'] == 'UNVERIFIED'
