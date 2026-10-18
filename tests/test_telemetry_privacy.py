"""Observability must help debug the flow without exporting sensitive content."""
import json

import pytest

pytest.importorskip("cryptography")
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi.testclient import TestClient

from callgate.confirmation import ConfirmationCoordinator
from callgate.review_transport import create_broker_app
from callgate.sentry_observability import sanitize_mapping
from callgate.verification import DemoVerificationGate
from callgate.workflow import DemoWorkflow


ORIGIN = "http://127.0.0.1:8766"
PARTICIPANT = "participant-secret-token"
REVIEWER = "reviewer-secret-token"


def bearer(token):
    return {"Authorization": "Bearer " + token}


def broker_with_capture(captured):
    issuer = Ed25519PrivateKey.generate()
    reviewer = Ed25519PrivateKey.generate()
    coordinator = ConfirmationCoordinator("issuer", issuer, {"reviewer": reviewer.public_key()})
    workflow = DemoWorkflow(coordinator, DemoVerificationGate({"issuer": issuer.public_key()}), "reviewer")
    workflow.set_processing_consent(True)
    return create_broker_app(workflow, PARTICIPANT, REVIEWER, origin=ORIGIN,
                             telemetry_transport=captured.append)


def test_observability_never_exports_transcript_amount_or_contact_fields():
    captured = []
    app = broker_with_capture(captured)
    with TestClient(app, base_url=ORIGIN) as client:
        assert client.post('/api/transcript', json={
            'segment_id': 's-private', 'revision': 0,
            'text': 'Send 9876543 dollars to Alice right now secret phrase',
            'language': 'en', 'start_ms': 0, 'end_ms': 1000, 'final': True,
        }, headers=bearer(PARTICIPANT)).status_code == 200
        assert client.post('/api/request', json={
            'destination': 'alice-private-wallet',
            'amount_cents': 9876543,
        }, headers=bearer(PARTICIPANT)).status_code == 200
        assert client.post('/api/protected-action', json={
            'destination': 'alice-private-wallet',
            'amount_cents': 9876543,
        }, headers=bearer(PARTICIPANT)).status_code == 403

    exported = json.dumps(captured, sort_keys=True)
    assert captured
    for forbidden in [
        'Send 9876543 dollars', 'secret phrase', '9876543',
        'alice-private-wallet', 'Alice', 'reviewer',
    ]:
        assert forbidden not in exported
    assert 'session_hash' in exported
    assert 'CHALLENGED' in exported
    assert 'POLICY_PROOF_REQUIRED' in exported


def test_sanitize_mapping_drops_sensitive_fields_and_hashes_session():
    clean = sanitize_mapping({
        'text': 'Tell me your verification code',
        'destination': 'private-wallet',
        'amount_cents': 12345,
        'claimed_identity': 'saved-family',
        'session_id': 'session-123',
        'risk_state': 'CHALLENGED',
        'error_code': 'POLICY_PROOF_REQUIRED',
    })
    assert clean == {
        'session_hash': 'b9c84322f82434cb',
        'risk_state': 'CHALLENGED',
        'error_code': 'POLICY_PROOF_REQUIRED',
    }
