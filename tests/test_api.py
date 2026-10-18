from fastapi.testclient import TestClient
from callgate.api import app
import pytest
from starlette.websockets import WebSocketDisconnect
from callgate.models import Transcript

client = TestClient(app)
S = dict(segment_id="s", text="Send money right now", start_ms=0, end_ms=1000, final=True)


def test_replay_and_schema():
    assert client.get("/health").status_code == 200
    assert client.post("/v1/replay", json={"segments": [S]}).json()["state"] == "CHALLENGED"
    assert client.post("/v1/replay", json={"segments": [dict(S, verified=True)]}).status_code == 422
    assert client.post("/v1/replay", json={"segments": []}).status_code == 422


def test_websocket_isolation_and_recovery():
    with client.websocket_connect("/v1/stream/transcript") as ws:
        ws.send_json(dict(S, verified=True))
        assert ws.receive_json()["error"] == "invalid_segment"
        ws.send_json(S)
        assert ws.receive_json()["state"] == "CHALLENGED"
    with client.websocket_connect("/v1/stream/transcript") as ws:
        ws.send_json(dict(S, text="Hello"))
        assert ws.receive_json()["state"] == "UNVERIFIED"


def test_audio_requires_key(monkeypatch):
    monkeypatch.delenv("ASSEMBLYAI_API_KEY", raising=False)
    with client.websocket_connect("/v1/stream/audio") as ws:
        assert ws.receive_json()["error"] == "assemblyai_not_configured"


def test_demo_and_external_origin_rejected():
    assert client.get("/").status_code == 200
    assert client.get("/demo-assets/pcm-worklet.js").status_code == 200
    assert client.get("/.env").status_code == 404
    for endpoint in ("audio", "transcript"):
        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect(f"/v1/stream/{endpoint}", headers={"origin":"https://untrusted.example"}):
                pass


def test_audio_websocket_pipeline(monkeypatch):
    monkeypatch.setenv("ASSEMBLYAI_API_KEY", "test-key")
    async def provider(chunks, on_segment):
        received = []
        async for chunk in chunks:
            received.append(chunk)
        assert received == [b'\0' * 3200]
        await on_segment(Transcript(segment_id="a1",text="Send money. Do not tell anyone.",start_ms=0,end_ms=1000,final=True))
    monkeypatch.setattr("callgate.api.stream_pcm", provider)
    with client.websocket_connect("/v1/stream/audio") as ws:
        ws.send_bytes(b'\0' * 3200)
        ws.send_text('{"type":"stop"}')
        assert ws.receive_json()["risk"]["state"] == "COOLING_OFF"
        assert ws.receive_json()["type"] == "completed"


def test_audio_failure_is_sanitized(monkeypatch):
    monkeypatch.setenv("ASSEMBLYAI_API_KEY", "test-key")
    async def denied(chunks, on_segment):
        raise PermissionError("secret-must-not-be-returned")
    monkeypatch.setattr("callgate.api.stream_pcm", denied)
    with client.websocket_connect("/v1/stream/audio") as ws:
        result = ws.receive_json()
        assert result == {"error":"network_permission", "protected_actions_allowed":False}


def test_provider_error_categories():
    from callgate.api import audio_error_code
    from types import SimpleNamespace
    import asyncio
    assert audio_error_code(asyncio.TimeoutError()) == "stream_timeout"
    for status, expected in [(401,"provider_auth"),(403,"provider_auth"),(429,"provider_limit")]:
        error = RuntimeError("sensitive")
        error.response = SimpleNamespace(status_code=status)
        assert audio_error_code(error) == expected
