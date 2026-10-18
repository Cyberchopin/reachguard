"""API-key-free proof rehearsal: forced detector failure plus approved utility.

Synthetic integration demonstration only; not population-level evaluation.
No evaluation_v2 inputs, real calls or real financial systems are used.
"""
import json
from fastapi.testclient import TestClient
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from callgate.confirmation import ConfirmationCoordinator, ReviewerDecision, decision_bytes
from callgate.review_transport import create_broker_app
from callgate.safety_policy import SafetyConversation
from callgate.verification import DemoVerificationGate
from callgate.workflow import DemoWorkflow
from callgate.models import Transcript


class EmptyDetector:
    def extract(self, segment):
        return []


def rehearsal():
    issuer, reviewer = Ed25519PrivateKey.generate(), Ed25519PrivateKey.generate()
    coordinator = ConfirmationCoordinator('local-demo', issuer, {'reviewer': reviewer.public_key()})
    gate = DemoVerificationGate({'local-demo': issuer.public_key()})
    workflow = DemoWorkflow(coordinator, gate, 'reviewer')
    workflow.set_processing_consent(True)
    # Test-only counterfactual injection; no public runtime configuration toggle.
    workflow._conversation = SafetyConversation(EmptyDetector())
    row = Transcript(segment_id='counterfactual', text='Send money now. Do not tell anyone.',
                     final=True, start_ms=0, end_ms=1000)
    risk = workflow.ingest(row)
    app = create_broker_app(workflow, 'participant-proof', 'reviewer-proof')
    with TestClient(app, base_url='http://127.0.0.1:8766') as client:
        response = client.post('/api/protected-action',
            json={'destination':'fictional-wallet','amount_cents':100},
            headers={'Authorization':'Bearer participant-proof'})
    assert risk['state'] == 'UNVERIFIED'
    assert response.status_code == 403
    assert workflow.status()['outcome'] is None
    counterfactual = {'forced_detector':'empty_events', 'risk_state':risk['state'],
                      'http_status':response.status_code, 'response':response.json()}
    workflow.reset_session()
    workflow.set_processing_consent(True)
    workflow.ingest(row.model_copy(update={'text':'Send money.', 'segment_id':'legitimate-demo'}))
    bundle = workflow.request_confirmation(destination='fictional-wallet', amount_cents=100)
    request = bundle['request']
    decision = ReviewerDecision(request=request, approved=True,
        signature=reviewer.sign(decision_bytes(request, True)).hex())
    approved = workflow.complete(decision, challenge_response=bundle['out_of_band_challenge'])
    assert approved['status'] == 'simulated_action_completed'
    assert approved['real_action_executed'] is False
    return {'mode':'synthetic_protocol_rehearsal_not_accuracy_evaluation',
            'counterfactual':counterfactual,
            'valid_simulated_approval':approved['status'],
            'real_action_executed':False,
            'reviewer':'generated_local_test_key_not_independent_human'}


if __name__ == '__main__':
    print(json.dumps(rehearsal(), indent=2))
