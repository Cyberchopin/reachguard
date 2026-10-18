"""Run the connected local workflow with explicitly simulated reviewer keys."""
import json
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from callgate.confirmation import ConfirmationCoordinator, ReviewerDecision, decision_bytes
from callgate.verification import DemoVerificationGate
from callgate.workflow import DemoWorkflow
from callgate.models import Transcript


def run():
    issuer, reviewer = Ed25519PrivateKey.generate(), Ed25519PrivateKey.generate()
    workflow = DemoWorkflow(
        ConfirmationCoordinator('demo', issuer, {'reviewer': reviewer.public_key()}),
        DemoVerificationGate({'demo': issuer.public_key()}), 'reviewer')
    workflow.set_processing_consent(True)
    risk = workflow.ingest(Transcript(segment_id='s1', final=True, start_ms=0, end_ms=1000,
        text='Move your savings into the secure holding wallet.'))
    bundle = workflow.request_confirmation(destination='demo-wallet', amount_cents=280000)
    request = bundle['request']
    decision = ReviewerDecision(request=request, approved=True,
        signature=reviewer.sign(decision_bytes(request, True)).hex())
    result = workflow.complete(decision, challenge_response=bundle['out_of_band_challenge'])
    assert risk['state'] == 'CHALLENGED'
    assert result['status'] == 'simulated_action_completed'
    return dict(risk_state=risk['state'], result=result,
        reviewer='generated_test_key_not_human', transport='in_process_not_independent_channel')


if __name__ == '__main__':
    print(json.dumps(run(), indent=2))
