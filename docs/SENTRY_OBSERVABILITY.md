# Sentry observability

Implemented: optional privacy-bounded hooks for the local simulator. Not implemented: a committed DSN, public production telemetry, Session Replay setup, or proof that an external Sentry project received events.

## What is instrumented

The broker emits trace/log records around these demo steps:

| Step | Purpose | Sensitive fields deliberately omitted |
|---|---|---|
| `transcript_to_evidence` | Measure local parsing and policy update time | Transcript text |
| `policy_decision` | Record the resulting state name | Transcript text and caller content |
| `challenge_request` | Measure challenge creation | Amount, destination, contact identity and challenge code |
| `reviewer_decision` | Measure signed reviewer completion | Reviewer identity, challenge response and operation details |
| `gateway_refused` | Record direct protected-action refusal | Amount and destination |

Only `session_hash`, state names, event types, durations, outcome status and error codes are intended to leave the process.

## Runtime configuration

Set `CALLGATE_SENTRY_DSN` in the process environment to enable Sentry. The DSN is not read from code or committed files.

```bash
CALLGATE_SENTRY_DSN=... python -m scripts.start_review_demo
```

If `sentry-sdk` is not installed or the DSN is absent, the demo still runs and no outbound Sentry event is sent.

## Privacy guard

`callgate.sentry_observability` sets `send_default_pii=False` and uses event filters before Sentry receives events. The tests use a fake transport and assert that a sensitive transcript, a plain amount, a destination and contact-like fields are absent from emitted records.

Run:

```bash
python -m pytest tests/test_telemetry_privacy.py -q -p no:cacheprovider
```

## Honest demo note

This repository does not yet contain a real "observability changed the implementation" record from a live Sentry trace. If that happens during the hackathon, record the timestamp, observed trace/log, code change and before/after measured output in `BUILD_LOG.md`. If it does not happen, say so.
