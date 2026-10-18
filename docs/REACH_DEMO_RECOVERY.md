# Frozen Reach demo: recovery and remaining verification

Functionality is frozen. These are operator recovery instructions, not automatic restart actions. Run from the repository root in WSL with the existing `.venv`. First confirm which component failed. Do not restart a healthy component, start duplicate agents, reset a database, regenerate credentials or run `.test-tmp/device-live/stop.py` (it stops the device service too). The current session has not been restarted for this handoff.

## Current components and boundaries

| Component | Local origin / route | Existing private runtime |
| --- | --- | --- |
| Device inbox | `http://127.0.0.1:8780/`, POST `/api/device-events` | `.test-tmp/device-live/` |
| Original ngrok device tunnel | Agent API `http://127.0.0.1:4040/api/tunnels`; only upstream 8780 | `ngrok.yml`, `ngrok.pid`, `ngrok-base-url.txt` in device runtime |
| Independent help | `http://127.0.0.1:8783/` Dashboard, `/contact` contact page | `.test-tmp/help-live/` |
| Separate localhost.run help tunnel | Only upstream 8783; public `/contact` and `/` | `localhostrun.pid`, `localhostrun.log`, `localhostrun-known-hosts`, `help-base-url.txt` in help runtime |
| Legacy payment demo (optional) | Fusion/participant 8781, reviewer 8782 | `.test-tmp/fusion-live/` — remains local, not a help dependency |

Public origins stay in ignored runtime files, not source. The help free domain has already rotated while the SSH process stayed alive. A running PID alone is insufficient: verify the actual HTML and authenticated API before distributing an address. First inspect the latest accepted forwarding event; a different live origin may already exist without needing a restart. Only share HTTPS origins. No credential belongs in a URL query or recovery log.

## Recover the 8780 service only if it is down

The original `.test-tmp/device-live/start_local.py` is an initial provisioning script: it creates credentials with exclusive file creation and is **not** a restart recipe. Do not delete existing credential files to make it run. Instead, this recipe reloads the existing credentials into the child process without printing them and reuses the existing database. It refuses to start while the port is listening and never provisions missing files:

```bash
.venv/bin/python - <<'PY'
import json, os, socket, subprocess
from pathlib import Path
root = Path.cwd()
runtime = root / '.test-tmp/device-live'
with socket.socket() as check:
    if check.connect_ex(('127.0.0.1', 8780)) == 0:
        raise SystemExit('8780 is already listening; leave it running.')
required = [runtime / name for name in ('device.token', 'viewer.token', 'events.sqlite3')]
if not all(path.is_file() for path in required):
    raise SystemExit('Existing runtime files missing; restore them, do not provision replacements.')
os.umask(0o077)
env = os.environ.copy()
env['CALLGATE_DEVICE_TOKENS'] = json.dumps({'nano-01': required[0].read_text().strip()})
env['CALLGATE_DEVICE_VIEWER_TOKEN'] = required[1].read_text().strip()
env['CALLGATE_DEVICE_DB'] = str(required[2])
with (runtime / 'service.log').open('ab') as log:
    process = subprocess.Popen([str(root / '.venv/bin/python'), '-m', 'scripts.start_device_events'],
        cwd=root, env=env, stdin=subprocess.DEVNULL, stdout=log, stderr=log, start_new_session=True)
(runtime / 'service.pid').write_text(str(process.pid))
print('Device service started with existing runtime; verify HTTP before use.')
PY
```

Verify local `/` is HTML 200 and unauthenticated `/api/device-events` returns 401. A service-only restart does not require restarting a healthy ngrok tunnel. This recovery recipe was reviewed, not executed against the running service during the freeze.

## Recover the original ngrok tunnel only if it is down

Check the local agent API on 4040 and the PID command before starting another agent. With local 8780 healthy and the old agent confirmed stopped, use the existing executable and private configuration, without opening/printing the config or changing the account/domain:

```bash
.test-tmp/device-live/ngrok http http://127.0.0.1:8780 \
  --config .test-tmp/device-live/ngrok.yml --inspect=false \
  --log .test-tmp/device-live/ngrok-recovery.log --log-format=json
```

Keep that terminal running. Never target 8781/8782 or request a made-up custom domain. Read only `public_url` and `config.addr` from `http://127.0.0.1:4040/api/tunnels`; verify the target is exactly `http://127.0.0.1:8780`. Confirm the actual URL against the saved origin and phone App/Shortcut before resuming. Do not assume an address survived merely because startup succeeded. Check unauthenticated API 401; only use a distinctly labeled Local test event if a new write test is needed. Do not automatically retry failed agent startup.

## Recover independent help service only if it is down

First retain `.test-tmp/help-live/credentials.json`, all role files, `help.sqlite3` and the source inbox DB. Do not start with a fresh runtime directory: that would create different roles and state. The current launcher reloads existing identities and derives the matching device route.

```bash
.venv/bin/python -m scripts.start_help_demo \
  --inbox-db .test-tmp/device-live/events.sqlite3 \
  --runtime-dir .test-tmp/help-live --port 8783
```

Keep the terminal running. Verify local Dashboard/contact HTML 200 and help API 401 without access. Existing contact/owner/dashboard codes must still work for their respective roles. A service restart alone does not require restarting a healthy SSH tunnel. This restart path was not exercised on the live phone session during the freeze.

## Recover or refresh the separate help HTTPS origin

If the SSH PID is healthy, first extract the latest registered forwarding origin using the lookup below and test it. The earlier No tunnel incident needed only this refresh. Do not mistake `admin.localhost.run` for the forwarding origin.

Only when the old SSH process is confirmed stopped, start one new connection in a terminal. It exposes only help 8783, uses no private SSH identity/agent, and retains its private known-hosts file:

```bash
ssh -F /dev/null -T \
  -o BatchMode=yes -o IdentitiesOnly=yes -o IdentityFile=/dev/null \
  -o IdentityAgent=none \
  -o UserKnownHostsFile=.test-tmp/help-live/localhostrun-known-hosts \
  -o StrictHostKeyChecking=accept-new -o ConnectTimeout=12 \
  -o ConnectionAttempts=1 -o ExitOnForwardFailure=yes \
  -o ServerAliveInterval=30 -o ServerAliveCountMax=3 \
  -R 80:127.0.0.1:8783 nokey@localhost.run -- --output json \
  >> .test-tmp/help-live/localhostrun.log 2>&1
```

Keep that terminal running; do not install a retry loop. In another terminal, after the accepted forwarding event arrives:

```bash
.venv/bin/python - <<'PY'
import json, re
from pathlib import Path
runtime = Path('.test-tmp/help-live')
origins = []
for line in (runtime / 'localhostrun.log').read_text(errors='replace').splitlines():
    try:
        event = json.loads(line)
    except ValueError:
        continue
    if event.get('type') == 'v1.tcpip_forward.register.accepted':
        origins.extend(re.findall(r'https://[a-z0-9-]+\.lhr\.life', line))
if not origins:
    raise SystemExit('No accepted forwarding origin found; do not distribute an address.')
print('Candidate contact URL:', origins[-1] + '/contact')
print('Verify HTML 200 and role authentication before updating help-base-url.txt or sharing.')
PY
```

This prints no credentials and does not treat a historic log entry as proof of current connectivity. After a successful public HTML/API check, update only the private `help-base-url.txt` to the verified origin. If a new process is started manually, record its correct PID after inspecting its command, so a stale `localhostrun.pid` is not later used for stopping. Sharing a new help URL does not change the device upload URL. A free domain may rotate again; this is not stable hosting. Original ngrok and all databases remain untouched.

## Frozen final-demo verification gaps

- Arduino button → BLE delivery to the actual iPhone App, GATT details/ACK semantics and the teammate's foreground Swift gateway have not been verified.
- The phone Shortcut → backend → iPhone contact acceptance → Dashboard path succeeded once, operator-confirmed with matching persisted receipt/acceptance. Rehearse again before judging; identify a new event explicitly instead of presenting the already-accepted event as a new request.
- Real iPhone unable-to-help, owner cancellation, network loss/retry and concurrent response/cancellation have not been demonstrated on phones. Backend synthetic tests cover those transitions and role boundaries; they are not phone evidence.
- End-to-end same-alarm retry across the firmware/Swift gateway has not been verified. It must reuse event_id; a BLE ACK alone is only phone receipt.
- OS/browser variants, long-duration tunnel/domain stability and restart recovery have not been validated on the live demo. Recovery instructions are documented without interrupting it.
- Automated contact notification, escalation, location, emergency dispatch and proof that help arrived are not implemented. Keep them outside demo claims, rather than treating them as working integrations awaiting a test.

No new features should be added for this frozen demo. Do not expose the local payment demo to solve tunnel issues. Refer to [the observed iPhone evidence](IPHONE_HELP_VERIFICATION_2026-10-17.md) and keep runtime secrets/data outside commits.
