"""One non-business smoke trace/log via existing privacy filters; safe diagnostics.

No runtime files are changed. --from-service reads configuration privately from
the selected live process; otherwise uses this shell's exported configuration.
"""
import argparse
from email.utils import parsedate_to_datetime
from collections import Counter
from datetime import datetime, timezone
import importlib.metadata
import logging
import os
import re
from pathlib import Path
import sys
import time

from sentry_sdk.transport import HttpTransport
from sentry_sdk.utils import Dsn
import sentry_sdk
from callgate import reach_observability as telemetry


class DiagnosticTransport(HttpTransport):
    def __init__(self, options):
        self.captured = Counter()
        self.sent = Counter()
        self.responses = []
        self.losses = Counter()
        self.failures = []
        self.current_types = []
        self.log_metadata = []
        super().__init__(options)

    def capture_envelope(self, envelope):
        self.captured.update(item.headers['type'] for item in envelope.items)
        for item in envelope.items:
            if item.headers['type'] == 'log':
                import json
                payload = json.loads(item.get_bytes())
                for log in payload.get('items', []):
                    self.log_metadata.append({'timestamp_utc': datetime.fromtimestamp(log['timestamp'], timezone.utc).isoformat(),
                        'age_seconds': round(time.time()-log['timestamp'],2),
                        'trace_id': log.get('trace_id'),
                        'body_is_fixed_operation': log.get('body') == 'reach.operation',
                        'step_is_smoke_test': log.get('attributes',{}).get('reach.step',{}).get('value') == 'observability.smoke_test'})
        return super().capture_envelope(envelope)

    def _send_envelope(self, envelope):
        self.current_types = [item.headers['type'] for item in envelope.items]
        return super()._send_envelope(envelope)

    def _request(self, method, endpoint_type, body, headers):
        try:
            response = super()._request(method, endpoint_type, body, headers)
        except Exception as error:
            # Class names only: exception messages may contain keys or URLs.
            self.failures.append(type(error).__name__)
            raise
        self.responses.append({'items': list(self.current_types), 'http_status': response.status,
            'server_clock_delta_seconds': round(time.time()-parsedate_to_datetime(response.headers['Date']).timestamp(),1) if response.headers.get('Date') else None,
            'response_content_type': response.headers.get('Content-Type','').split(';')[0]
                if response.headers.get('Content-Type','').split(';')[0] in {'application/json','text/html','text/plain'} else 'other',
            'response_body_bytes': len(response.data),
            'rate_limit_header_present': bool(response.headers.get('X-Sentry-Rate-Limits')),
            'retry_after_present': bool(response.headers.get('Retry-After')),
            'server_error_header_present': bool(response.headers.get('X-Sentry-Error'))})
        if 200 <= response.status < 300:
            self.sent.update(self.current_types)
        return response

    def record_lost_event(self, reason, data_category=None, item=None, **kwargs):
        category = item.data_category if item else data_category
        self.losses[(str(reason), str(category))] += 1
        return super().record_lost_event(reason, data_category, item, **kwargs)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--from-service', choices=['device-live', 'help-live'])
    parser.add_argument('--canonical-ingest-path', action='store_true',
                        help='Probe only: remove extra cloud-ingest DSN path prefix; never edit service configuration.')
    args = parser.parse_args()
    if args.from_service:
        root = Path(__file__).resolve().parents[1]
        pid = (root/'.test-tmp'/args.from_service/'service.pid').read_text().strip()
        proc = Path('/proc')/pid
        command = (proc/'cmdline').read_bytes().split(b'\0')
        expected = b'scripts.start_device_events' if args.from_service == 'device-live' else b'scripts.start_help_demo'
        if expected not in command or (proc/'cwd').resolve() != root:
            raise SystemExit('Unexpected service PID; aborting without sending.')
        env = dict(entry.split(b'=',1) for entry in (proc/'environ').read_bytes().split(b'\0') if b'=' in entry)
        # Reproduce the service's DSN and network/certificate environment, not
        # credentials for any business endpoint. Never print these values.
        names = ['CALLGATE_SENTRY_DSN','CALLGATE_SENTRY_TRACES_SAMPLE_RATE',
                 'HTTP_PROXY','HTTPS_PROXY','ALL_PROXY','NO_PROXY','http_proxy','https_proxy','all_proxy','no_proxy',
                 'SSL_CERT_FILE','SSL_CERT_DIR','REQUESTS_CA_BUNDLE','CURL_CA_BUNDLE']
        for name in names:
            if name.encode() in env:
                os.environ[name] = env[name.encode()].decode()
            else:
                os.environ.pop(name, None)
        print('Probe configuration copied privately from', args.from_service, 'PID', pid)
    dsn = os.environ.get('CALLGATE_SENTRY_DSN')
    if not dsn:
        raise SystemExit('Export CALLGATE_SENTRY_DSN in this shell, or select --from-service.')
    parsed = Dsn(dsn)
    print('SDK version:', importlib.metadata.version('sentry-sdk'))
    print('DSN numeric project ID:', parsed.project_id)
    host_type = ('sentry_ingest' if re.fullmatch(r'o\d+\.ingest(?:\.[a-z]+)?\.sentry\.io', parsed.host)
                 else 'sentry_web' if parsed.host in {'sentry.io','www.sentry.io'} else 'other')
    print('DSN endpoint classification:', host_type)
    print('DSN path prefix empty:', not parsed.path or parsed.path == '/')
    print('DSN key hex format:', bool(re.fullmatch(r'[a-f0-9]{32}', parsed.public_key)))
    if args.canonical_ingest_path:
        if host_type != 'sentry_ingest':
            raise SystemExit('Path correction is restricted to standard Sentry cloud ingest hosts.')
        os.environ['CALLGATE_SENTRY_DSN'] = telemetry.canonical_cloud_ingest_dsn(dsn)
        print('Probe-only canonical ingest path selected; live configuration unchanged.')
    print('Proxy configured:', any(os.environ.get(k) for k in ['HTTP_PROXY','HTTPS_PROXY','ALL_PROXY','http_proxy','https_proxy','all_proxy']))
    # Suppress raw SDK diagnostics; transport records sanitized outcomes instead.
    logging.getLogger('sentry_sdk').disabled = True
    if not telemetry.configure_reach_sentry(transport=DiagnosticTransport):
        raise SystemExit('SDK initialization failed; details omitted.')
    client = sentry_sdk.get_client()
    transport = client.transport
    print('Probe Logs enabled:', client.options['enable_logs'])
    print('Probe trace sample rate nonzero:', client.options['traces_sample_rate'] > 0)
    print('Privacy filters active:', client.options['before_send_log'] is telemetry.filter_log,
          client.options['before_send_transaction'] is telemetry.filter_transaction)
    print('Smoke test UTC:', datetime.now(timezone.utc).isoformat())
    with telemetry.operation('observability.smoke_test'):
        pass  # One fixed labelled log and one transaction; no business API calls.
    started = time.monotonic()
    sentry_sdk.flush(timeout=20)
    print('Flush elapsed seconds:', round(time.monotonic()-started, 2))
    print('Envelopes queued by item type:', dict(transport.captured))
    print('Smoke log metadata (no payload/credentials):', transport.log_metadata)
    print('HTTP 2xx by item type:', dict(transport.sent))
    print('HTTP outcomes:', transport.responses)
    print('Network exception classes:', transport.failures)
    print('SDK lost items:', [{'reason':reason,'category':category,'count':count}
                            for (reason,category),count in transport.losses.items()])
    print('Probe worker pending items:', transport._worker._queue.unfinished_tasks)
    print('Probe log batch pending:', len(client.log_batcher._buffer))
    print('HTTP 2xx means ingestion accepted the envelope, not UI indexing confirmation.')
    accepted = transport.sent['transaction'] > 0 and transport.sent['log'] > 0
    client.close(timeout=1)
    if not accepted:
        raise SystemExit('Smoke test delivery NOT confirmed for both Trace and Log; inspect sanitized outcomes above.')


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print('Probe failed; exception class only:', type(error).__name__)
        sys.exit(1)
