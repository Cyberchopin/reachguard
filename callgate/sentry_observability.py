"""Privacy-bounded observability hooks for the local demo.

Sentry is optional at runtime. The exported records deliberately keep only
state names, event types, hashes, timing and error codes; transcript text,
plain amounts and contact identifiers are not telemetry fields.
"""
from __future__ import annotations

from contextlib import contextmanager
import hashlib
import os
import time


_transport = None
_sentry_sdk = None


SENSITIVE_KEYS = {
    'amount', 'amount_cents', 'challenge', 'challenge_response', 'claimed_identity',
    'contact', 'destination', 'identity', 'operation', 'request', 'text', 'transcript',
}
ALLOWED_KEYS = {
    'authorization_denied', 'code', 'duration_ms', 'enrollment', 'error_code',
    'event_type', 'outcome_status', 'pending', 'policy_state', 'processing_allowed',
    'risk_state', 'schema_version', 'session_hash', 'span_status', 'step',
}


def session_hash(session_id: str) -> str:
    return hashlib.sha256(session_id.encode()).hexdigest()[:16]


def sanitize_mapping(fields: dict) -> dict:
    clean = {}
    for key, value in fields.items():
        if key in SENSITIVE_KEYS:
            continue
        if key == 'session_id':
            clean['session_hash'] = session_hash(str(value))
            continue
        if key in ALLOWED_KEYS and (isinstance(value, (str, int, float, bool)) or value is None):
            clean[key] = value
    return clean


def configure_sentry(*, dsn: str | None = None, transport=None):
    """Initialize Sentry when CALLGATE_SENTRY_DSN is present.

    Tests may pass a transport callable to capture sanitized outbound records.
    """
    global _transport, _sentry_sdk
    _transport = transport
    dsn = dsn if dsn is not None else os.environ.get('CALLGATE_SENTRY_DSN')
    if not dsn:
        return False
    try:
        import sentry_sdk
    except ImportError:
        return False

    def before_send(event, hint):
        return _sanitize_sentry_event(event)

    def before_send_transaction(event, hint):
        return _sanitize_sentry_event(event)

    sentry_sdk.init(
        dsn=dsn,
        send_default_pii=False,
        before_send=before_send,
        before_send_transaction=before_send_transaction,
        traces_sample_rate=float(os.environ.get('CALLGATE_SENTRY_TRACES_SAMPLE_RATE', '1.0')),
    )
    _sentry_sdk = sentry_sdk
    return True


def _sanitize_sentry_event(event):
    if not isinstance(event, dict):
        return event
    event.pop('request', None)
    event.pop('user', None)
    contexts = event.get('contexts')
    if isinstance(contexts, dict):
        contexts.pop('trace', None)
    tags = event.get('tags')
    if isinstance(tags, dict):
        event['tags'] = sanitize_mapping(tags)
    extra = event.get('extra')
    if isinstance(extra, dict):
        event['extra'] = sanitize_mapping(extra)
    spans = event.get('spans')
    if isinstance(spans, list):
        for span in spans:
            if isinstance(span, dict):
                data = span.get('data')
                if isinstance(data, dict):
                    span['data'] = sanitize_mapping(data)
    return event


def log_security(event_type: str, **fields):
    payload = {'schema_version': 'callgate-telemetry-v1', 'event_type': event_type,
               **sanitize_mapping(fields)}
    if _transport is not None:
        _transport(dict(payload))
    if _sentry_sdk is not None:
        _sentry_sdk.set_context('callgate', payload)
        _sentry_sdk.capture_message('callgate.' + event_type, level='info')
    return payload


@contextmanager
def trace_step(step: str, **fields):
    start = time.perf_counter()
    span = None
    if _sentry_sdk is not None:
        span = _sentry_sdk.start_span(op='callgate.' + step, description=step)
        span.__enter__()
        for key, value in sanitize_mapping(fields).items():
            span.set_data(key, value)
    try:
        yield
    except Exception:
        duration = round((time.perf_counter() - start) * 1000, 3)
        log_security('span', step=step, duration_ms=duration, span_status='error', **fields)
        raise
    else:
        duration = round((time.perf_counter() - start) * 1000, 3)
        log_security('span', step=step, duration_ms=duration, span_status='ok', **fields)
    finally:
        if span is not None:
            span.__exit__(None, None, None)
