"""Opt-in Reach tracing and real Sentry Logs; no request/identity collection."""
from contextlib import contextmanager
from functools import wraps
import os
import re
import time
from urllib.parse import urlsplit, urlunsplit

_sdk = None
STEPS = frozenset({
    'observability.smoke_test',
    'device.upload', 'device.persist', 'help.sync', 'help.persist',
    'help.response', 'help.read', 'help.list', 'help.cancel', 'help.rotate',
})


def canonical_cloud_ingest_dsn(value):
    """Explicit routing correction only; retain key, host and numeric project."""
    from sentry_sdk.utils import Dsn
    parsed = Dsn(value)
    if not re.fullmatch(r'o\d+\.ingest(?:\.[a-z]+)?\.sentry\.io', parsed.host):
        raise ValueError('Canonical routing is restricted to Sentry cloud ingest.')
    parts = urlsplit(value)
    return urlunsplit(parts._replace(path='/'+parsed.project_id, query='', fragment=''))


def _trace(context):
    # Keep correlation, never framework/request baggage.
    return {k: v for k, v in context.items()
            if k in {'trace_id', 'span_id', 'parent_span_id'}
            and isinstance(v, str) and re.fullmatch(r'[a-f0-9]{16}|[a-f0-9]{32}', v)}


def filter_transaction(event, hint):
    if event.get('transaction') not in STEPS:
        return None
    clean = {k: event[k] for k in ('type', 'event_id', 'start_timestamp', 'timestamp') if k in event}
    clean['transaction'] = event['transaction']
    clean['contexts'] = {'trace': _trace(event.get('contexts', {}).get('trace', {}))}
    clean['contexts']['trace']['op'] = 'reach'
    clean['spans'] = []
    for span in event.get('spans', []):
        if span.get('description') in STEPS:
            clean['spans'].append({**_trace(span), 'op': 'reach',
                'description': span['description'],
                **{k: span[k] for k in ('start_timestamp', 'timestamp', 'status') if k in span}})
    return clean


def filter_log(log, hint):
    if log.get('body') != 'reach.operation':
        return None
    raw = log.get('attributes', {})
    attrs = {k: v.get('value') if isinstance(v, dict) else v for k, v in raw.items()}
    if attrs.get('reach.step') not in STEPS:
        return None
    allowed = {'reach.step': attrs['reach.step']}
    if attrs.get('reach.outcome') in {'ok', 'error'}:
        allowed['reach.outcome'] = attrs['reach.outcome']
    for key in ('reach.duration_ms', 'reach.http_status'):
        value = attrs.get(key)
        if type(value) in (int, float):
            allowed[key] = value
    # The SDK normalizes callback output to typed envelope values.
    return {**{k: log[k] for k in ('time_unix_nano', 'trace_id', 'span_id', 'severity_text', 'severity_number') if k in log},
            'body': 'reach.operation', 'attributes': allowed}


def configure_reach_sentry(*, transport=None):
    global _sdk
    if _sdk is not None:
        return True
    dsn = os.environ.get('CALLGATE_SENTRY_DSN')
    if not dsn:
        return False
    try:
        import sentry_sdk
        from sentry_sdk import logger  # Load the public structured Logs API.
        rate = float(os.environ.get('CALLGATE_SENTRY_TRACES_SAMPLE_RATE', '1.0'))
        if not 0 <= rate <= 1:
            return False
        sentry_sdk.init(
            dsn=dsn, transport=transport, traces_sample_rate=rate,
            enable_logs=True, default_integrations=False,
            auto_enabling_integrations=False, send_default_pii=False,
            include_local_variables=False, include_source_context=False,
            max_request_body_size='never', max_breadcrumbs=0,
            auto_session_tracking=False, send_client_reports=False,
            server_name='', trace_propagation_targets=[],
            before_send=lambda event, hint: None,
            before_send_transaction=filter_transaction, before_send_log=filter_log,
        )
    except (ImportError, ValueError, TypeError):
        # No exception detail: a malformed DSN can contain private configuration.
        print('Reach telemetry disabled: check local SDK/configuration; values omitted.', flush=True)
        return False
    _sdk = sentry_sdk
    print('Reach telemetry enabled: Tracing + Logs; privacy filters active.', flush=True)
    return True


@contextmanager
def operation(step):
    if step not in STEPS:
        raise ValueError('Unknown telemetry operation')
    if _sdk is None:
        yield {}
        return
    span = (_sdk.start_span(op='reach', description=step) if _sdk.get_current_span()
            else _sdk.start_transaction(op='reach', name=step))
    with span:
        start = time.perf_counter()
        fields = {}
        outcome = 'ok'
        try:
            yield fields
        except Exception:
            outcome = 'error'
            span.set_status('internal_error')
            raise
        finally:
            if fields.get('reach.http_status', 200) >= 400:
                outcome = 'error'
            from sentry_sdk import logger
            logger.info('reach.operation', attributes={
                'reach.step': step, 'reach.outcome': outcome,
                'reach.duration_ms': round((time.perf_counter()-start)*1000, 3),
                **fields,
            })


def observed(step):
    def decorate(function):
        @wraps(function)
        def wrapped(*args, **kwargs):
            with operation(step):
                return function(*args, **kwargs)
        return wrapped
    return decorate


def instrument_http(app, device=False):
    @app.middleware('http')
    async def telemetry(request, call_next):
        path = request.url.path
        step = None
        if device and path == '/api/device-events' and request.method == 'POST':
            step = 'device.upload'
        elif not device:
            if path == '/api/help-requests' and request.method == 'GET':
                step = 'help.list'
            elif re.fullmatch(r'/api/help-requests/[^/]+', path) and request.method == 'GET':
                step = 'help.read'
            elif re.fullmatch(r'/api/help-requests/[^/]+/responses', path):
                step = 'help.response'
            elif re.fullmatch(r'/api/help-requests/[^/]+/cancel', path):
                step = 'help.cancel'
        if step is None:
            return await call_next(request)
        with operation(step) as fields:
            response = await call_next(request)
            fields['reach.http_status'] = response.status_code
            return response
