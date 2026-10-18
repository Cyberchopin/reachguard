"""Isolated device intent inbox. Deliberately imports no approval workflow."""
import hmac
import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, ConfigDict, Field


class DeviceEvent(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    event_id: str = Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9_.:-]+$")
    device_id: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_.:-]+$")
    event_type: Literal["verify_request", "help_request"]


def create_app(*, device_tokens: dict[str, str], viewer_token: str, db_path: str):
    values = [*device_tokens.values(), viewer_token]
    if (not device_tokens or any(not isinstance(t, str) or len(t) < 32 or not t.isascii()
                                 or any(c.isspace() for c in t) for t in values)
            or len(set(values)) != len(values)):
        raise ValueError("Provide distinct ASCII credentials of at least 32 characters")
    for device_id in device_tokens:
        DeviceEvent(event_id="config", device_id=device_id, event_type="help_request")
    tokens = dict(device_tokens)
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

    @contextmanager
    def connect():
        db = sqlite3.connect(db_path, timeout=10)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    with connect() as db:
        db.execute("CREATE TABLE IF NOT EXISTS device_events (event_id TEXT PRIMARY KEY, device_id TEXT NOT NULL, event_type TEXT NOT NULL, received_at TEXT NOT NULL)")

    def credential(request: Request):
        scheme, _, value = request.headers.get("authorization", "").partition(" ")
        if scheme.lower() != "bearer" or not value or not value.isascii():
            raise HTTPException(401, "Bearer credential required", headers={"WWW-Authenticate": "Bearer"})
        return value

    def device_auth(value: str = Depends(credential)):
        for device_id, token in tokens.items():
            if hmac.compare_digest(value, token):
                return device_id
        raise HTTPException(401, "Invalid device credential")

    def viewer_auth(value: str = Depends(credential)):
        if not hmac.compare_digest(value, viewer_token):
            raise HTTPException(401, "Invalid viewer credential")

    @app.exception_handler(RequestValidationError)
    async def validation_error(request, exc):
        # Do not echo input (which might contain accidentally supplied secrets).
        return JSONResponse({"detail": "Invalid event schema"}, status_code=422)

    @app.middleware("http")
    async def boundaries(request, call_next):
        if request.method == "POST":
            size = 0
            chunks = []
            async for chunk in request.stream():
                size += len(chunk)
                chunks.append(chunk)
                if size > 2048:
                    return JSONResponse({"detail": "Body too large"}, status_code=413)
            request._body = b"".join(chunks)
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; frame-ancestors 'none'; base-uri 'none'"
        return response

    @app.post("/api/device-events")
    def receive(event: DeviceEvent, device_id: str = Depends(device_auth)):
        if event.device_id != device_id:
            raise HTTPException(403, "Device credential mismatch")
        timestamp = datetime.now(timezone.utc).isoformat()
        with connect() as db:
            inserted = db.execute("INSERT OR IGNORE INTO device_events VALUES (?, ?, ?, ?)",
                                  (event.event_id, event.device_id, event.event_type, timestamp)).rowcount
            stored = dict(db.execute("SELECT * FROM device_events WHERE event_id = ?", (event.event_id,)).fetchone())
            if stored["device_id"] != event.device_id or stored["event_type"] != event.event_type:
                raise HTTPException(409, "event_id already used for another event")
        return JSONResponse({"status": "received" if inserted else "duplicate", "event": stored,
                             "intent_only": True}, status_code=201 if inserted else 200)

    @app.get("/api/device-events", dependencies=[Depends(viewer_auth)])
    def recent():
        with connect() as db:
            rows = db.execute("SELECT * FROM device_events ORDER BY rowid DESC LIMIT 100").fetchall()
        return {"events": [dict(row) for row in rows], "intent_only": True}

    @app.get("/", response_class=HTMLResponse)
    def dashboard():
        return Path(__file__).with_name("device_events.html").read_text(encoding="utf-8")

    return app


def from_env():
    """Read only explicitly configured inbox credentials; never load .env files."""
    try:
        tokens = json.loads(os.environ["CALLGATE_DEVICE_TOKENS"])
        viewer = os.environ["CALLGATE_DEVICE_VIEWER_TOKEN"]
        if not isinstance(tokens, dict):
            raise ValueError()
        return create_app(device_tokens=tokens, viewer_token=viewer,
                          db_path=os.environ.get("CALLGATE_DEVICE_DB", "device-events.sqlite3"))
    except (KeyError, ValueError, TypeError):
        raise RuntimeError("Invalid device inbox configuration; see docs/DEVICE_EVENTS.md") from None
