import pytest
from test_workflow import setup, sign


def test_reviewer_denial_cannot_be_bypassed_by_changing_amount():
    workflow, reviewer, bundle, _ = setup()
    workflow.complete(sign(reviewer, bundle, False))
    with pytest.raises(ValueError, match='denied'):
        workflow.request_confirmation(destination='other-wallet', amount_cents=280001)


def test_expired_request_cannot_be_reissued_for_the_same_session():
    workflow, reviewer, bundle, clock = setup()
    clock[0] += 121
    with pytest.raises(ValueError, match='expired'):
        workflow.complete(sign(reviewer, bundle), challenge_response=bundle['out_of_band_challenge'])
    with pytest.raises(ValueError, match='denied'):
        workflow.request_confirmation(destination='demo-wallet', amount_cents=280000)
