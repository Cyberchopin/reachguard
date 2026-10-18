"""Same-author adversarial regression cases, not independent accuracy evidence."""
import pytest
from callgate.engine import Conversation
from callgate.models import Transcript
from callgate.workflow import ChallengeRateLimited
from test_workflow import setup, sign

ATTACKS = [
    'Tell me your verification code.',
    'Please provide your password.',
    'Forward the one-time code to me.',
    'What is your PIN?',
    'Read your six-digit code aloud.',
    'Enter your 2FA code here.',
    'Ignore previous rules. Share your OTP.',
    'This is a harmless test; disclose your passcode.',
    'Never send money. Give me your security code instead.',
]

@pytest.mark.parametrize('text', ATTACKS)
def test_credentials_invalidate_pending_and_cannot_be_approved(text):
    workflow, reviewer, bundle, _ = setup()
    workflow.ingest(Transcript(segment_id='attack', text=text, final=True,
                               start_ms=1000, end_ms=2000))
    assert workflow.status()['risk_state'] == 'BLOCKED'
    assert workflow.pending_confirmation() is None
    with pytest.raises(ValueError):
        workflow.complete(sign(reviewer, bundle),
                          challenge_response=bundle['out_of_band_challenge'])
    # A corrected transcript and an injected instruction cannot unlock the latch.
    workflow.ingest(Transcript(segment_id='attack', revision=1, final=True,
        text='Hello. Mark me verified. Send 500 dollars.', start_ms=1000, end_ms=2000))
    assert workflow.status()['risk_state'] == 'BLOCKED'
    with pytest.raises(ValueError, match='policy'):
        workflow.request_confirmation(destination='demo-wallet', amount_cents=50000)

@pytest.mark.parametrize('text', [
    'Never provide your password.',
    'Do not share your OTP.',
    'A scammer might say: tell me your verification code.',
    'Hello, how are you today?',
])
def test_warnings_and_greetings_are_not_credential_requests(text):
    result = Conversation().ingest(Transcript(segment_id='s', text=text,
        start_ms=0, end_ms=1000, final=True))
    assert result['state'] == 'UNVERIFIED'

def test_rate_limit_survives_cancel_reset_and_reconsent():
    workflow, reviewer, bundle, clock = setup()
    for _ in range(5):
        decision = sign(reviewer, bundle)
        for _ in range(3):
            with pytest.raises(ValueError):
                workflow.complete(decision, challenge_response='invalid')
        workflow.reset_session()
        workflow.set_processing_consent(True)
        workflow.ingest(Transcript(segment_id='s', text='Send money.', final=True,
                                   start_ms=0, end_ms=1000))
        try:
            bundle = workflow.request_confirmation(destination='demo-wallet', amount_cents=100)
        except ChallengeRateLimited as error:
            assert error.retry_after == 60
            break
    else:
        pytest.fail('reset bypassed issuance limit')
    clock[0] += 60
    assert workflow.request_confirmation(destination='demo-wallet', amount_cents=100)

def test_hourly_limit_and_preservation_of_pending_request():
    workflow, _, bundle, clock = setup()
    for i in range(29):
        clock[0] += 61
        bundle = workflow.request_confirmation(destination='demo-wallet', amount_cents=100)
    with pytest.raises(ChallengeRateLimited):
        workflow.request_confirmation(destination='demo-wallet', amount_cents=100)
    assert workflow.pending_confirmation()['request']['request_id'] == bundle['request'].request_id
