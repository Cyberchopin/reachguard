"""Explicit operator restart; retain private runtime and leave tunnels untouched.

Run with the existing .venv from a shell with exported Sentry configuration.
--verify-only never restarts anything and needs no DSN in its own environment.
"""
import fcntl
import importlib.metadata
import json
import os
from pathlib import Path
import re
import signal
import sqlite3
import subprocess
import sys
import time
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
D = ROOT / '.test-tmp/device-live'
H = ROOT / '.test-tmp/help-live'
MARKER = b'Reach telemetry enabled: Tracing + Logs; privacy filters active.'


def require(condition, message):
    if not condition:
        raise SystemExit(message)


def listeners(port):
    result = subprocess.run(['ss', '-ltnpH', f'sport = :{port}'],
                            capture_output=True, check=True, text=True)
    return result.stdout


def owned_process(runtime, port, module):
    output = listeners(port)
    if not output.strip():
        # Also reject a running but not-yet-listening launcher with a saved PID.
        pidfile = runtime / 'service.pid'
        if pidfile.exists():
            proc = Path('/proc') / pidfile.read_text().strip()
            if proc.exists() and (proc/'cwd').resolve() == ROOT:
                args = (proc/'cmdline').read_bytes().split(b'\0')
                require(module.encode() not in args, f'{port}: launcher still running; stop and inspect.')
        return None
    require((runtime/'service.pid').is_file(), f'{port}: missing PID file; refusing to stop unknown listener.')
    pid = int((runtime/'service.pid').read_text())
    proc = Path('/proc') / str(pid)
    args = (proc/'cmdline').read_bytes().split(b'\0')
    owners = {int(p) for p in re.findall(r'pid=(\d+)', output)}
    require(owners == {pid} and f'127.0.0.1:{port}' in output,
            f'{port}: unexpected listener ownership; refusing restart.')
    require((proc/'cwd').resolve() == ROOT and b'-m' in args and module.encode() in args,
            f'{port}: saved PID is not the expected launcher; refusing restart.')
    return pid


def http(base, path, token=None, payload=None, timeout=15):
    headers = {'ngrok-skip-browser-warning': '1'}
    if token:
        headers['Authorization'] = 'Bearer '+token
    if payload is not None:
        headers['Content-Type'] = 'application/json'
    request = urllib.request.Request(base+path, headers=headers,
        data=None if payload is None else json.dumps(payload).encode())
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as error:
        return error.code, b''


def startup_ready(runtime, port, pid, offset):
    """A reserved listening socket alone does not mean initialization finished."""
    if f'pid={pid},' not in listeners(port):
        return False
    with (runtime/'service.log').open('rb') as log:
        log.seek(offset)
        if MARKER not in log.read():
            return False
    try:
        return http(f'http://127.0.0.1:{port}', '/', timeout=1)[0] == 200
    except (OSError, urllib.error.URLError):
        return False


def verify_origin(device, help_origin):
    for origin, path in [(device, '/'), (help_origin, '/'), (help_origin, '/contact')]:
        require(http(origin, path)[0] == 200, 'HTML verification failed; inspect tunnel/service locally (address omitted).')
    require(http(device, '/api/device-events')[0] == 401, 'Device authorization boundary failed.')
    require(http(help_origin, '/api/help-requests')[0] == 401, 'Help authorization boundary failed.')
    token = (D/'device.token').read_text().strip()
    require(http(help_origin, '/api/help-requests', token)[0] == 401, 'Device role isolation failed.')
    for role in ('owner', 'contact', 'dashboard'):
        code, body = http(help_origin, '/api/help-requests', (H/(role+'.token')).read_text().strip())
        require(code == 200 and json.loads(body)['role'] == role, 'Existing help role verification failed.')
        if role == 'dashboard':
            records = json.loads(body)['requests']
            if records:
                require(http(help_origin, '/api/help-requests/'+records[0]['event_id'],
                             (H/'dashboard.token').read_text().strip())[0] == 200, 'Status read failed.')
    # Repeat an existing event exactly: exercise upload/persistence without a new alarm.
    with sqlite3.connect((D/'events.sqlite3').as_uri()+'?mode=ro', uri=True) as db:
        row = db.execute("SELECT event_id,device_id,event_type FROM device_events WHERE device_id='nano-01' AND event_type='help_request' ORDER BY rowid DESC LIMIT 1").fetchone()
    if row:
        code, body = http(device, '/api/device-events', token, dict(zip(('event_id','device_id','event_type'), row)))
        require(code == 200 and json.loads(body)['status'] == 'duplicate', 'Existing-event retry failed.')
        print('Upload duplicate retry: PASS (no new alarm).')
    else:
        print('No existing alarm available; upload retry check skipped.')
    print('HTML, role access, device isolation and status reads: PASS.')


def verify():
    verify_origin('http://127.0.0.1:8780', 'http://127.0.0.1:8783')
    print('Local business checks: PASS.')
    code, body = http('http://127.0.0.1:4040', '/api/tunnels')
    require(code == 200, 'ngrok API unavailable; tunnels were not restarted.')
    urls = [t['public_url'] for t in json.loads(body)['tunnels']
            if t['public_url'].startswith('https://') and t['config']['addr'] == 'http://127.0.0.1:8780']
    require(len(urls) == 1, 'Expected one HTTPS ngrok tunnel to 8780.')
    origins = []
    for line in (H/'localhostrun.log').read_text(errors='replace').splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if event.get('type') == 'v1.tcpip_forward.register.accepted':
            origins.extend(re.findall(r'https://[a-z0-9-]+\.lhr\.life', line))
    require(origins, 'No accepted help origin; tunnels were not restarted.')
    verify_origin(urls[0], origins[-1])
    for runtime, name, origin in [(D, 'ngrok-base-url.txt', urls[0]), (H, 'help-base-url.txt', origins[-1])]:
        changed = not (runtime/name).exists() or (runtime/name).read_text().strip() != origin
        (runtime/name).write_text(origin+'\n')
        print(name, 'CHANGED; verified address saved locally; notify teammates securely.' if changed else 'verified (address omitted).')
    print('Public business checks: PASS. Sentry project receipt still requires checking Sentry UI.')


def main():
    os.chdir(ROOT)
    os.umask(0o077)
    if sys.argv[1:] == ['--verify-only']:
        verify()
        return
    canonical_path = sys.argv[1:] == ['--canonical-sentry-path']
    require(not sys.argv[1:] or canonical_path,
            'Usage: python -m scripts.restart_reach_observed [--verify-only | --canonical-sentry-path]')
    for runtime, names in [(D, ('device.token','viewer.token','events.sqlite3')),
                           (H, ('credentials.json','owner.token','contact.token','dashboard.token','help.sqlite3'))]:
        require(all((runtime/name).is_file() for name in names), 'Required existing runtime missing; nothing restarted.')
    require(os.environ.get('CALLGATE_SENTRY_DSN'), 'Export CALLGATE_SENTRY_DSN in this shell; nothing restarted.')
    from sentry_sdk.utils import Dsn
    parsed = Dsn(os.environ['CALLGATE_SENTRY_DSN'])  # Validate locally; never display it.
    if canonical_path:
        from callgate.reach_observability import canonical_cloud_ingest_dsn
        os.environ['CALLGATE_SENTRY_DSN'] = canonical_cloud_ingest_dsn(os.environ['CALLGATE_SENTRY_DSN'])
        print('Canonical cloud ingest routing selected; DSN key, host and project preserved; value omitted.')
    elif re.fullmatch(r'o\d+\.ingest(?:\.[a-z]+)?\.sentry\.io', parsed.host):
        require(parsed.path == '/', 'Unexpected cloud DSN path prefix; nothing restarted. Verify project DSN or use --canonical-sentry-path explicitly.')
    version = tuple(int(x) for x in importlib.metadata.version('sentry-sdk').split('.')[:2])
    require((2, 72) <= version < (3, 0), 'Use the tested Sentry SDK >=2.72,<3; nothing restarted.')
    rate = float(os.environ['CALLGATE_SENTRY_TRACES_SAMPLE_RATE'])
    require(0 < rate <= 1, 'Export a sampling rate in (0,1]; nothing restarted.')
    identities = json.loads((H/'credentials.json').read_text())
    require({r['role'] for r in identities} == {'owner','contact','dashboard'}, 'Existing roles invalid; nothing restarted.')
    for row in identities:
        require((H/(row['role']+'.token')).read_text().strip() == row['token'], 'Existing role files disagree; nothing restarted.')
    env = os.environ.copy()
    env.update(CALLGATE_DEVICE_TOKENS=json.dumps({'nano-01': (D/'device.token').read_text().strip()}),
               CALLGATE_DEVICE_VIEWER_TOKEN=(D/'viewer.token').read_text().strip(),
               CALLGATE_DEVICE_DB=str(D/'events.sqlite3'))
    specs = [(D, 8780, 'scripts.start_device_events', []),
             (H, 8783, 'scripts.start_help_demo', ['--inbox-db',str(D/'events.sqlite3'),'--runtime-dir',str(H),'--port','8783'])]
    # Reject concurrent copies; validate both owners before stopping either service.
    with (H/'observed-restart.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        owners = [owned_process(runtime, port, module) for runtime,port,module,args in specs]
        for (runtime, port, module, args), pid in zip(specs, owners):
            if pid is not None:
                # Recheck ownership immediately before sending the graceful signal.
                require(owned_process(runtime, port, module) == pid, 'Ownership changed; aborting.')
                os.kill(pid, signal.SIGTERM)
                for _ in range(100):
                    proc = Path('/proc')/str(pid)
                    exited = not proc.exists() or (proc/'stat').read_text().split(') ',1)[1].startswith('Z')
                    if exited and not listeners(port).strip():
                        break
                    time.sleep(0.2)
                else:
                    raise SystemExit(f'{port}: graceful shutdown timed out; no forced kill or duplicate start.')
            require(not listeners(port).strip(), f'{port}: occupied; refusing duplicate start.')
            logfile = runtime/'service.log'
            offset = logfile.stat().st_size if logfile.exists() else 0
            with logfile.open('ab') as log:
                child = subprocess.Popen([str(ROOT/'.venv/bin/python'), '-m', module, *args],
                    cwd=ROOT, env=env, stdin=subprocess.DEVNULL, stdout=log, stderr=log, start_new_session=True)
            (runtime/'service.pid').write_text(str(child.pid))
            for _ in range(100):
                require(child.poll() is None, f'{port}: new process exited; no automatic retry. Inspect service.log locally.')
                if startup_ready(runtime, port, child.pid, offset):
                    break
                time.sleep(0.2)
            else:
                raise SystemExit(f'{port}: HTTP/telemetry readiness timed out; inspect existing process before any restart. No duplicate start attempted.')
            print(f'{port}: running PID {child.pid}; Tracing + Logs enabled, privacy filters active.')
        print('Services restarted. Tunnels were not stopped or reconfigured.')
        verify()


if __name__ == '__main__':
    try:
        main()
    except Exception:
        # Suppress exception payloads that could contain DSNs/HTTP credential details.
        raise SystemExit('Restart/check failed; configuration details omitted. No automatic retry. Inspect local state before rerunning.') from None
