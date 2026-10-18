"""Security boundaries for the disposable, two-process reviewer demo."""
import time
import asyncio
import threading
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

pytest.importorskip("cryptography")
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from callgate.confirmation import ConfirmationCoordinator, ConfirmationRequest, ReviewerDecision, decision_bytes
from callgate.review_transport import create_broker_app, create_reviewer_app
from callgate.verification import DemoVerificationGate
from callgate.workflow import DemoWorkflow
from callgate.models import Transcript


BROKER_ORIGIN = "http://127.0.0.1:8766"
REVIEWER_ORIGIN = "http://127.0.0.1:8767"
PARTICIPANT_TOKEN = "participant-test-token-" + "a" * 32
REVIEWER_TOKEN = "reviewer-test-token-" + "b" * 32
SEGMENT = dict(segment_id="s", revision=0, text="Send money right now.",
               start_ms=0, end_ms=1000, final=True, role="caller")


def bearer(token, **extra):
    return {"Authorization": f"Bearer {token}", **extra}


def test_direct_protected_action_is_closed_even_when_detector_is_benign(demo):
    demo.broker.post('/api/transcript', json=dict(SEGMENT, text='Hello.'),
                     headers=bearer(PARTICIPANT_TOKEN))
    response = demo.broker.post('/api/protected-action',
        json={'destination': 'demo-wallet', 'amount_cents': 100},
        headers=bearer(PARTICIPANT_TOKEN))
    assert response.status_code == 403
    assert response.json()['detail']['code'] == 'POLICY_PROOF_REQUIRED'
    assert demo.workflow.status()['outcome'] is None


def test_challenge_issuance_returns_429_and_retry_after(demo):
    demo.broker.post('/api/transcript', json=SEGMENT, headers=bearer(PARTICIPANT_TOKEN))
    for _ in range(5):
        response = demo.broker.post('/api/request',
            json={'destination': 'demo-wallet', 'amount_cents': 100},
            headers=bearer(PARTICIPANT_TOKEN))
        assert response.status_code == 200
    response = demo.broker.post('/api/request',
        json={'destination': 'demo-wallet', 'amount_cents': 100},
        headers=bearer(PARTICIPANT_TOKEN))
    assert response.status_code == 429
    assert 1 <= int(response.headers['Retry-After']) <= 60


@pytest.fixture
def demo():
    issuer_key = Ed25519PrivateKey.generate()
    reviewer_key = Ed25519PrivateKey.generate()
    clock = [int(time.time())]
    coordinator = ConfirmationCoordinator(
        "issuer", issuer_key, {"reviewer": reviewer_key.public_key()},
        clock=lambda: clock[0],
    )
    gate = DemoVerificationGate({"issuer": issuer_key.public_key()}, clock=lambda: clock[0])
    workflow = DemoWorkflow(coordinator, gate, "reviewer")
    workflow.set_processing_consent(True)
    broker_app = create_broker_app(workflow, PARTICIPANT_TOKEN, REVIEWER_TOKEN,
                                   origin=BROKER_ORIGIN)
    reviewer_app = create_reviewer_app(
        reviewer_key, REVIEWER_TOKEN, workflow.pending_confirmation,
        lambda submission: workflow.complete(
            submission.decision, challenge_response=submission.challenge_response),
        origin=REVIEWER_ORIGIN,
    )
    with TestClient(broker_app, base_url=BROKER_ORIGIN) as broker:
        with TestClient(reviewer_app, base_url=REVIEWER_ORIGIN) as reviewer:
            yield SimpleNamespace(broker=broker, reviewer=reviewer, workflow=workflow,
                                  reviewer_key=reviewer_key, clock=clock)


def request_action(demo, *, destination="demo-wallet", amount_cents=280000):
    response = demo.broker.post("/api/transcript", json=SEGMENT,
                               headers=bearer(PARTICIPANT_TOKEN, Origin=BROKER_ORIGIN))
    assert response.status_code == 200
    assert response.json()["state"] == "CHALLENGED"
    response = demo.broker.post("/api/request", json={
        "destination": destination, "amount_cents": amount_cents,
    }, headers=bearer(PARTICIPANT_TOKEN, Origin=BROKER_ORIGIN))
    assert response.status_code == 200
    return response.json()


def test_audio_ingress_shares_the_confirmation_workflow(demo, monkeypatch):
    monkeypatch.setenv('ASSEMBLYAI_API_KEY', 'test-key')
    monkeypatch.setenv('CALLGATE_ASR_USD_PER_HOUR', '0.12')

    async def provider(chunks, on_segment, **kwargs):
        received = []
        async for chunk in chunks:
            received.append(chunk)
        assert received == [b'\0' * 3200]
        await on_segment(Transcript(segment_id='voice-1', text='Send money right now.',
            start_ms=0, end_ms=1000, final=True, role='caller'))

    monkeypatch.setattr('callgate.review_transport.stream_pcm', provider)
    ws_headers = {'Origin': BROKER_ORIGIN, 'Host': '127.0.0.1:8766'}
    with demo.broker.websocket_connect('/api/audio', headers=ws_headers) as ws:
        ws.send_json({'type': 'authenticate', 'token': PARTICIPANT_TOKEN})
        ws.send_bytes(b'\0' * 3200)
        ws.send_text('{"type":"stop"}')
        update = ws.receive_json()
        assert update['risk']['state'] == 'CHALLENGED'
        assert update['metrics']['audio_received_ms'] == 100.0
        assert update['metrics']['risk_engine_ms'] >= 0
        assert update['metrics']['estimated_asr_cost_usd'] == 0.00000333
        completed = ws.receive_json()
        assert completed['type'] == 'completed'
        assert completed['session_metrics']['cost_scope'] == 'asr_only_configured_rate'
    summary = demo.broker.get('/api/metrics/summary',
                              headers=bearer(PARTICIPANT_TOKEN)).json()
    assert summary['sessions'] == 1 and summary['completed'] == 1
    # Mock supplies 100ms of PCM but claims end_ms=1000; this is not valid latency evidence.
    assert summary['failed'] == 0 and summary['alert_samples'] == 0
    bundle = demo.broker.post('/api/request', json={
        'destination': 'demo-wallet', 'amount_cents': 100,
    }, headers=bearer(PARTICIPANT_TOKEN)).json()
    assert bundle['out_of_band_challenge'].isdigit()
    assert len(bundle['out_of_band_challenge']) == 6


def test_audio_ingress_requires_participant_capability(demo):
    ws_headers = {'Origin': BROKER_ORIGIN, 'Host': '127.0.0.1:8766'}
    with demo.broker.websocket_connect('/api/audio', headers=ws_headers) as ws:
        ws.send_json({'type': 'authenticate', 'token': REVIEWER_TOKEN})
        with pytest.raises(WebSocketDisconnect):
            ws.receive_json()


@pytest.mark.parametrize('route,body', [('/api/session/reset', {}),
    ('/api/processing-consent', {'granted': False})])
def test_server_stops_idle_provider_without_browser_cooperation(demo, monkeypatch, route, body):
    monkeypatch.setenv('ASSEMBLYAI_API_KEY', 'test-key')
    started, stopped = threading.Event(), threading.Event()
    async def provider(chunks, on_segment, **kwargs):
        started.set()
        try:
            await asyncio.Future()
        finally:
            stopped.set()
    monkeypatch.setattr('callgate.review_transport.stream_pcm', provider)
    with demo.broker.websocket_connect('/api/audio', headers={
        'Origin': BROKER_ORIGIN, 'Host': '127.0.0.1:8766'}) as ws:
        ws.send_json({'type':'authenticate', 'token':PARTICIPANT_TOKEN})
        assert started.wait(2)
        blocked = demo.broker.post('/api/request', json={
            'destination':'demo-wallet', 'amount_cents':100}, headers=bearer(PARTICIPANT_TOKEN))
        assert blocked.status_code == 409
        assert blocked.json()['detail'] == 'finish audio before requesting confirmation'
        with demo.broker.websocket_connect('/api/audio', headers={
            'Origin': BROKER_ORIGIN, 'Host': '127.0.0.1:8766'}) as second:
            second.send_json({'type':'authenticate', 'token':PARTICIPANT_TOKEN})
            assert second.receive_json()['error'] == 'audio_already_active'
        response = demo.broker.post(route, json=body, headers=bearer(PARTICIPANT_TOKEN))
        assert response.status_code == 200
        assert stopped.wait(2)
        assert ws.receive_json()['error'] == 'processing_stopped'
    assert demo.workflow.status()['processing_allowed'] is False
    summary = demo.broker.get('/api/metrics/summary', headers=bearer(PARTICIPANT_TOKEN)).json()
    assert summary['cancelled'] == 1
    assert summary['failed'] == 0 and summary['failure_rate'] is None


def test_second_audio_connection_gets_a_fresh_segment_namespace(demo, monkeypatch):
    monkeypatch.setenv('ASSEMBLYAI_API_KEY', 'test-key')
    texts = iter(['Send money right now.', 'Tell me your verification code.'])

    async def provider(chunks, on_segment, **kwargs):
        async for _ in chunks:
            pass
        await on_segment(Transcript(segment_id='aai-0', text=next(texts),
            start_ms=0, end_ms=1000, final=True, role='caller'))

    monkeypatch.setattr('callgate.review_transport.stream_pcm', provider)
    headers = {'Origin': BROKER_ORIGIN, 'Host': '127.0.0.1:8766'}
    states = []
    for _ in range(2):
        with demo.broker.websocket_connect('/api/audio', headers=headers) as ws:
            ws.send_json({'type': 'authenticate', 'token': PARTICIPANT_TOKEN})
            ws.send_bytes(b'\0' * 3200)
            ws.send_text('{"type":"stop"}')
            states.append(ws.receive_json()['risk']['state'])
            assert ws.receive_json()['type'] == 'completed'
    assert states == ['CHALLENGED', 'BLOCKED']
    summary = demo.broker.get('/api/metrics/summary',
                              headers=bearer(PARTICIPANT_TOKEN)).json()
    assert summary['sessions'] == 2 and summary['failed'] == 0


def decision_json(demo, approved=True):
    request = ConfirmationRequest.model_validate(demo.workflow.pending_confirmation()["request"])
    return ReviewerDecision(
        request=request, approved=approved,
        signature=demo.reviewer_key.sign(decision_bytes(request, approved)).hex(),
    ).model_dump()


def submitted(decision, challenge_response=None):
    return {'decision': decision, 'challenge_response': challenge_response}


@pytest.mark.parametrize("approved,expected", [
    (True, "simulated_action_completed"), (False, "reviewer_denied"),
])
def test_participant_request_then_explicit_reviewer_decision(demo, approved, expected):
    # Non-ASCII text also exercises operation-hash serialization parity.
    bundle = request_action(demo, destination="Élodie 的 demo wallet")
    pending = demo.reviewer.get("/api/pending", headers=bearer(REVIEWER_TOKEN))
    assert pending.status_code == 200
    assert pending.json() == {k: bundle[k] for k in ('request', 'operation')}
    payload = {"request_id": bundle["request"]["request_id"], "approved": approved,
               "challenge_response": bundle['out_of_band_challenge'] if approved else None}
    response = demo.reviewer.post("/api/decide", json=payload,
                                 headers=bearer(REVIEWER_TOKEN, Origin=REVIEWER_ORIGIN))
    assert response.status_code == 200
    assert response.json()["status"] == expected
    assert response.json()["real_action_executed"] is False
    assert demo.workflow.pending_confirmation() is None
    assert demo.reviewer.post("/api/decide", json=payload,
                              headers=bearer(REVIEWER_TOKEN)).status_code == 409


def test_no_confirmation_cannot_be_approved(demo):
    for client, route in [(demo.broker, "/api/review/pending"),
                          (demo.reviewer, "/api/pending")]:
        response = client.get(route, headers=bearer(REVIEWER_TOKEN))
        assert response.status_code == 200
        assert response.json() is None
    response = demo.reviewer.post("/api/decide", json={
        "request_id": "0" * 64, "approved": True,
    }, headers=bearer(REVIEWER_TOKEN))
    assert response.status_code == 409


def test_withdrawal_over_transport_clears_evidence_and_pending_action(demo):
    request_action(demo)
    response = demo.broker.post('/api/processing-consent', json={'granted': False},
                                headers=bearer(PARTICIPANT_TOKEN))
    assert response.status_code == 200
    assert response.json()['processing_consent'] == 'REVOKED'
    status = demo.broker.get('/api/status', headers=bearer(PARTICIPANT_TOKEN)).json()
    assert status['risk_state'] == 'UNVERIFIED'
    assert status['processing_allowed'] is False
    assert status['pending'] is False
    blocked = demo.broker.post('/api/transcript', json=SEGMENT,
                               headers=bearer(PARTICIPANT_TOKEN))
    assert blocked.status_code == 409


@pytest.mark.parametrize("client_name,method,route,body", [
    ("broker", "GET", "/api/review/pending", None),
    ("broker", "POST", "/api/review/decision", {}),
    ("reviewer", "GET", "/api/pending", None),
    ("reviewer", "POST", "/api/decide", {"request_id": "x", "approved": True}),
])
def test_participant_token_cannot_access_reviewer_routes(demo, client_name, method, route, body):
    response = getattr(demo, client_name).request(
        method, route, json=body, headers=bearer(PARTICIPANT_TOKEN))
    assert response.status_code in {401, 403}


@pytest.mark.parametrize("route,body", [
    ("/api/transcript", SEGMENT),
    ("/api/request", {"destination": "demo", "amount_cents": 100}),
    ("/api/processing-consent", {"granted": True}),
    ("/api/session/reset", {}),
])
def test_reviewer_token_cannot_act_as_participant(demo, route, body):
    response = demo.broker.post(route, json=body, headers=bearer(REVIEWER_TOKEN))
    assert response.status_code in {401, 403}


@pytest.mark.parametrize("client_name,route", [
    ("broker", "/api/review/pending"), ("reviewer", "/api/pending"),
])
@pytest.mark.parametrize("token", [None, "invalid-token"])
def test_missing_or_wrong_bearer_is_rejected(demo, client_name, route, token):
    response = getattr(demo, client_name).get(route, headers=bearer(token) if token else {})
    assert response.status_code in {401, 403}


@pytest.mark.parametrize("client_name,route,origin", [
    ("broker", "/api/review/pending", BROKER_ORIGIN),
    ("reviewer", "/api/pending", REVIEWER_ORIGIN),
])
def test_exact_origin_and_no_origin_server_requests(demo, client_name, route, origin):
    client = getattr(demo, client_name)
    for supplied in [None, origin]:
        extra = {} if supplied is None else {"Origin": supplied}
        response = client.get(route, headers=bearer(REVIEWER_TOKEN, **extra))
        assert response.status_code == 200
        assert "access-control-allow-origin" not in response.headers
    for invalid in ["null", "https://attacker.example", origin + "/",
                    origin.replace("127.0.0.1", "localhost"),
                    REVIEWER_ORIGIN if origin == BROKER_ORIGIN else BROKER_ORIGIN]:
        response = client.get(route, headers=bearer(REVIEWER_TOKEN, Origin=invalid))
        assert response.status_code == 403
        assert "access-control-allow-origin" not in response.headers


@pytest.mark.parametrize("client_name,route", [
    ("broker", "/api/review/pending"), ("reviewer", "/api/pending"),
])
@pytest.mark.parametrize("host", ["attacker.example", "localhost:8766", "127.0.0.1:9999"])
def test_untrusted_host_rejected(demo, client_name, route, host):
    response = getattr(demo, client_name).get(
        route, headers=bearer(REVIEWER_TOKEN, Host=host))
    assert response.status_code in {400, 403}


def test_signed_broker_submission_consumes_once_and_cannot_flip_denial(demo):
    request_action(demo)
    denial = decision_json(demo, approved=False)
    forged = dict(denial, approved=True)
    assert demo.broker.post("/api/review/decision", json=submitted(forged, '000000'),
                            headers=bearer(REVIEWER_TOKEN)).status_code == 409
    valid = demo.broker.post("/api/review/decision", json=submitted(denial),
                            headers=bearer(REVIEWER_TOKEN))
    assert valid.status_code == 200
    assert valid.json()["status"] == "reviewer_denied"
    assert demo.broker.post("/api/review/decision", json=submitted(denial),
                            headers=bearer(REVIEWER_TOKEN)).status_code == 409


@pytest.mark.parametrize("invalidate", ["revision", "replacement", "expiry"])
def test_stale_or_expired_decision_rejected_by_both_transports(demo, invalidate):
    bundle = request_action(demo)
    signed = decision_json(demo)
    if invalidate == "revision":
        response = demo.broker.post("/api/transcript", json=dict(SEGMENT, revision=1),
                                   headers=bearer(PARTICIPANT_TOKEN))
        assert response.status_code == 200
    elif invalidate == "replacement":
        # Identical operation still requires the newly created request ID.
        replacement = request_action(demo)
        assert replacement["request"]["request_id"] != bundle["request"]["request_id"]
    else:
        demo.clock[0] = bundle["request"]["expires_at"]
    payload = {"request_id": bundle["request"]["request_id"], "approved": True,
               "challenge_response": bundle['out_of_band_challenge']}
    assert demo.reviewer.post("/api/decide", json=payload,
                              headers=bearer(REVIEWER_TOKEN)).status_code == 409
    assert demo.broker.post("/api/review/decision",
                            json=submitted(signed, bundle['out_of_band_challenge']),
                            headers=bearer(REVIEWER_TOKEN)).status_code == 409


def test_changed_amount_hash_is_never_signed_or_submitted(demo):
    bundle = request_action(demo)
    submitted = []

    def tampered_pending():
        original = demo.workflow.pending_confirmation()
        return {**original, "operation": {**original["operation"], "amount_cents": 1}}

    app = create_reviewer_app(demo.reviewer_key, REVIEWER_TOKEN, tampered_pending,
                              submitted.append, origin=REVIEWER_ORIGIN)
    with TestClient(app, base_url=REVIEWER_ORIGIN) as client:
        response = client.post("/api/decide", json={
            "request_id": bundle["request"]["request_id"], "approved": True,
            "challenge_response": bundle['out_of_band_challenge'],
        }, headers=bearer(REVIEWER_TOKEN))
    assert response.status_code == 409
    assert submitted == []
    assert demo.workflow.pending_confirmation() is not None


@pytest.mark.parametrize("failure_stage", ["fetch", "submit"])
def test_upstream_failure_is_sanitized_and_keeps_confirmation_pending(demo, failure_stage):
    bundle = request_action(demo)
    secret = "private-upstream-error-must-not-leak"

    def failed(*args):
        raise OSError(secret)

    fetch = failed if failure_stage == "fetch" else demo.workflow.pending_confirmation
    submit = failed if failure_stage == "submit" else lambda submission: demo.workflow.complete(
        submission.decision, challenge_response=submission.challenge_response)
    app = create_reviewer_app(demo.reviewer_key, REVIEWER_TOKEN, fetch, submit,
                              origin=REVIEWER_ORIGIN)
    with TestClient(app, base_url=REVIEWER_ORIGIN) as client:
        if failure_stage == "fetch":
            response = client.get("/api/pending", headers=bearer(REVIEWER_TOKEN))
            assert response.status_code == 503
            assert secret not in response.text
        response = client.post("/api/decide", json={
            "request_id": bundle["request"]["request_id"], "approved": True,
            "challenge_response": bundle['out_of_band_challenge'],
        }, headers=bearer(REVIEWER_TOKEN))
    assert response.status_code == 503
    assert secret not in response.text
    assert demo.workflow.pending_confirmation() is not None
