# CallGate v2 phase 1

## Run locally

For the microphone test page, run `.venv/Scripts/python.exe scripts/start_demo.py` and open `http://127.0.0.1:8765/` in Chrome or Edge. The launcher reads the existing local `.env` without printing the key. Click Start and allow microphone access; no capture begins automatically. The page currently gives Chinese instructions for English test speech. Stop turns off the physical microphone immediately and sends generated trailing silence to finalize the provider turn. A test stops automatically after 60 seconds.

The browser requests a 16kHz AudioContext and checks the resulting rate, then uses an AudioWorklet to produce mono PCM16 in 100ms chunks. Browser WebSocket origins must match the local host/port. Keys are never served to the page. Static assets are restricted to the demo folder. Tests cover the audio WebSocket pipeline with a simulated provider and reject external browser origins. Actual microphone permissions/device behavior still require the user's own browser test.

Python 3.11+ (tested with Python 3.12 on Windows):

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements-lock.txt
.venv/Scripts/python.exe -m pytest -q
.venv/Scripts/python.exe -m callgate.bench
.venv/Scripts/python.exe -m uvicorn callgate.api:app --host 127.0.0.1 --port 8000 --ws-max-size 32768
```

Or install the package with `python -m pip install -e ".[dev]"`. The lock file records this session's tested dependency versions. The current upstream test client emits two deprecation warnings; the tests still pass.

Open `http://127.0.0.1:8000/docs` for the interactive API. No API key is required for transcript replay or ScamBench. This is a local development service, without authentication or multi-tenant protections; do not expose it publicly.

## Data path

16kHz mono PCM16 → AssemblyAI v3 Turn → Transcript → Extractor → validated RiskEvent → Conversation → score timeline + Guardian.

`callgate/models.py`: strict input contract, timestamps, bounded text, immutable input values. Extra authority fields are rejected.

`callgate/engine.py`: injectable Extractor protocol, English deterministic baseline, bounded conversation and timeline. Events refer to segment revision and character offsets; excerpts/secret values are not copied into event output. Revisions replace active evidence. Scores count each signal kind once across the conversation. Partial turns produce provisional scores only. Final turns affect policy. Unknown language/role stays explicit. Unknown speaker turns are analyzed conservatively; recipient turns are excluded when supplied by trusted ingress. The live adapter currently leaves roles unknown.

Guardian returns `LISTEN`, `VERIFY`, `PAUSE` or `DO_NOT_SHARE` with plain text. `emit` suppresses repeated notices. This is advice, not a payment block or automatic phone interruption. `protected_actions_allowed` is always false because capability issuance is not implemented. No score can verify identity. Scores are heuristic, not calibrated probabilities.

`BLOCKED` and `COOLING_OFF` remain sticky for the session after finalized evidence; later corrections may reduce the displayed score but cannot restore action permission. This can over-intervene after ASR errors. A future independent review/verification path must resolve these states; no untrusted reset exists.

## Interfaces

| Interface | Contract |
|---|---|
| GET `/health` | Baseline/version status |
| POST `/v1/replay` | `{"segments":[Transcript,...]}`; isolated conversation per request |
| WS `/v1/stream/transcript` | One Transcript JSON per message; risk state returned after each accepted revision |
| WS `/v1/stream/audio` | Binary PCM, 50–1000ms per message; send exact `{"type":"stop"}` text to finish; transcript+risk returned as turns arrive |

Example Transcript:

```json
{"segment_id":"turn-1","revision":0,"text":"Send money right now. Don't tell anyone.","start_ms":0,"end_ms":3000,"final":true,"role":"caller","language":"en"}
```

Expected final state: `COOLING_OFF`, score 70, Guardian `PAUSE`. `sequence` orders arrival; `audio_ms` is the audio clock, which may move backwards for delayed revisions. Same revision/same input is idempotent, stale revisions are ignored, conflicting same revisions rejected. A finalized turn cannot become partial.

## AssemblyAI audio smoke run

Live provider verification has now passed on two synthetic English samples (scam and benign). See `scambench/live-scam.json`, `scambench/live-benign.json` and BUILD_LOG.md. The provider adapter plus core engine were exercised; microphone capture and the complete local audio WebSocket route were not part of these two runs.

To repeat this direct provider/engine test with an explicitly chosen WAV and the local `.env` key, run `python scripts/live_smoke.py AUDIO.wav REPORT.json`. This exports transcripts, so use synthetic or consented test material only. It does not print or export the key.

Set `ASSEMBLYAI_API_KEY` in the server environment, then start the server. In a second terminal run:

```powershell
.venv/Scripts/python.exe scripts/stream_wav.py path-to-consented-mono-16khz.wav
```

This streams the file at realtime pace. A microphone/telephony producer can send the same PCM WebSocket protocol; device capture UI is deferred. Raw PCM is passed through in memory and not written to disk. Transcripts remain in the bounded in-memory conversation until disconnect/timeout; no secure-memory erasure is claimed. The audio route returns transcripts to the requesting local client. The WAV demo prints them, so avoid saving its terminal output for sensitive calls. Third-party audio retention is governed by the provider/account configuration, not this application.

The adapter authenticates using the Authorization header, deduplicates formatting-only repeats, handles provider errors, cancels companion tasks, bounds provider queues and times out final draining. Transcript idle timeout: 60s; audio idle timeout: 30s; audio session max: 30min. Session limits: 500 segments / 2000 updates. Reconnection/resume and persisted sessions are not implemented.

## Test evidence and next milestone

Tests cover replay, schema rejection, partial/final revision handling, cross-turn coercion, state latching, role/unsupported language behavior, capacity, session isolation and a simulated AssemblyAI transport. No real ASR accuracy, microphone capture, provider outage SLA, identity verification, or tool-security guarantee is established.

Next milestone: semantic extraction with evidence-span validation and no tools; separately authored held-out ScamBench cases; then one credentialed AssemblyAI run measuring end-of-speech→Guardian end-to-end latency. After that add independent verification and a simulated protected action. Bring in Pipecat or LiveKit when real two-party media/turn handling justifies it.
