"""Local development API: no persistence, public hosting or capability issuance."""
import asyncio
import json
import os
import logging
from pathlib import Path
from urllib.parse import urlsplit
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware
from pydantic import ValidationError
from .models import Replay, Transcript
from .engine import Conversation, EXTRACTOR_VERSION
from .assemblyai import stream_pcm

app = FastAPI(title="CallGate v2", version="0.2.0")
logger = logging.getLogger("uvicorn.error")


def audio_error_code(exc):
    """Return only fixed categories; never log provider exceptions or headers."""
    if isinstance(exc, PermissionError):
        return "network_permission"
    if isinstance(exc, asyncio.TimeoutError):
        return "stream_timeout"
    status = getattr(getattr(exc, "response", None), "status_code", None)
    if status in (401, 403):
        return "provider_auth"
    if status == 429:
        return "provider_limit"
    if isinstance(exc, (OSError, ConnectionError)):
        return "network_connection"
    return "audio_stream_failed"
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost", "testserver"])
DEMO = Path(__file__).parent / "demo"
app.mount("/demo-assets", StaticFiles(directory=DEMO), name="demo-assets")


@app.get("/", include_in_schema=False)
def microphone_demo():
    return FileResponse(DEMO / "index.html", headers={"Cache-Control": "no-store"})


async def local_origin(ws):
    origin = ws.headers.get("origin")
    if origin:
        parsed = urlsplit(origin)
        if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost"} or parsed.netloc != ws.headers.get("host"):
            await ws.close(code=1008)
            return False
    return True


@app.get("/health")
def health():
    return {"status": "ok", "extractor": EXTRACTOR_VERSION, "guardian": "advisory"}


@app.post("/v1/replay")
def replay(body: Replay, include_graph: bool = False):
    engine = Conversation()
    try:
        for segment in body.segments:
            engine.ingest(segment)
    except ValueError:
        raise HTTPException(422, "Invalid evidence or transcript revision")
    result = engine.snapshot()
    if include_graph:
        from .evidence_graph import evidence_graph
        result["evidence_graph"] = evidence_graph(engine)
    return result


@app.websocket("/v1/stream/transcript")
async def transcript_socket(ws: WebSocket):
    if not await local_origin(ws):
        return
    await ws.accept()
    engine = Conversation()
    try:
        while True:
            raw = await asyncio.wait_for(ws.receive_text(), 60)
            if len(raw) > 16000:
                await ws.close(code=1009)
                return
            try:
                segment = Transcript.model_validate_json(raw)
                await ws.send_json(engine.ingest(segment))
            except (ValidationError, ValueError):
                await ws.send_json({"error": "invalid_segment", "protected_actions_allowed": False})
    except WebSocketDisconnect:
        pass
    except asyncio.TimeoutError:
        await ws.close(code=1000, reason="idle timeout")


@app.websocket("/v1/stream/audio")
async def audio_socket(ws: WebSocket):
    if not await local_origin(ws):
        return
    await ws.accept()
    if not os.environ.get("ASSEMBLYAI_API_KEY"):
        await ws.send_json({"error": "assemblyai_not_configured"})
        await ws.close(code=1011)
        return
    engine = Conversation()
    sensor = None
    if os.environ.get("CALLGATE_VAD") == "silero":
        try:
            from .integrations.silero import SileroSensor
            sensor = SileroSensor()
        except Exception:
            # Optional audio sensor failure must not interrupt STT or grant trust.
            await ws.send_json({"sensor": {"type":"speech_activity", "status":"unavailable"}})

    async def chunks():
        nonlocal sensor
        while True:
            item = await asyncio.wait_for(ws.receive(), 30)
            if item["type"] == "websocket.disconnect":
                raise WebSocketDisconnect()
            if item.get("bytes") is not None:
                if sensor is not None:
                    try:
                        observations = await asyncio.to_thread(sensor.feed, item["bytes"])
                    except Exception:
                        sensor = None
                        observations = []
                        await ws.send_json({"sensor": {"type":"speech_activity", "status":"unavailable"}})
                    if observations:
                        await ws.send_json({"sensor": observations[-1]})
                yield item["bytes"]
            elif item.get("text") == '{"type":"stop"}':
                return
            else:
                raise ValueError("expected PCM bytes or stop")

    async def on_segment(segment):
        await ws.send_json({"transcript": segment.model_dump(), "risk": engine.ingest(segment)})

    try:
        await asyncio.wait_for(stream_pcm(chunks(), on_segment), timeout=1800)
        await ws.send_json({"type": "completed"})
        await ws.close()
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        # Never return provider exceptions/headers or raw transcript in error telemetry.
        code = audio_error_code(exc)
        logger.warning("CallGate audio failure category=%s exception_type=%s", code, type(exc).__name__)
        try:
            await ws.send_json({"error": code, "protected_actions_allowed": False})
            await ws.close(code=1011)
        except (WebSocketDisconnect, RuntimeError):
            pass
