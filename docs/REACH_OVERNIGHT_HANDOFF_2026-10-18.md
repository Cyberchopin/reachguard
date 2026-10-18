# Overnight operator handoff — 2026-10-18

## Current evidence, not assumptions

- **Software acknowledgement loop:** the labelled local HTTP request was persisted, the human operator clicked I can help, and the actual Dashboard showed accepted. Exact evidence and unmodified browser captures: [software rehearsal](REACH_SOFTWARE_TEST_2026-10-18.md). This is not a Shortcut or hardware run.
- **Upload telemetry:** the operator opened actual Sentry Trace `834071b8e04440bb806d78eb93449c3b` and confirmed `device.upload` and `device.persist`. Their server operation durations are distinct from network round-trip time and human waiting.
- **Contact-response telemetry:** still unverified. The successful acceptance in the database does not prove a matching Sentry Trace was viewed. Later background `help.sync` logs are not substituted for this event's import.
- **Latest hardware report:** the teammate reports real button → BLE → Swift → backend delivery and an App screenshot showing Medical / Recorded by backend (201). Direct read-only checks found both supplied event IDs as help requests; neither was accepted at the checked snapshot. See [hardware receipt reconciliation](REACH_HARDWARE_RECEIPTS_2026-10-18.md). This supersedes the earlier 401 as the latest reported upload outcome, without inventing a diagnosis or fix.

## Runtime snapshot and entry points

At **2026-10-18 08:35:53 UTC**, the existing device service (PID 6125), help service (PID 6138), ngrok (PID 1750) and help SSH tunnel (PID 4773) were running. Local device/help HTML returned 200. Public device and help HTML returned 200; APIs rejected unauthenticated reads with 401 and accepted their existing viewer/Dashboard roles with 200. A subsequent contact check verified the actual Reach `/contact` HTML and existing contact authorization, without a restart or contact response.

The free help origin rotated while SSH remained alive. Only the private verified-origin file was refreshed. An old URL returning No tunnel does not establish that the backend stopped. These are time-stamped checks, not overnight uptime guarantees.

Actual runtime remains **`/home/shiyue1128/callgate-voice-risk-protocol`**. The separate Git checkout used for publication is not the runtime. Do not replace the runtime with a new clone or copy its private files into Git.

In the runtime, these ignored files hold the last verified origins:

- `.test-tmp/device-live/ngrok-base-url.txt`: device upload origin; use `/api/device-events` for an HTTP client.
- `.test-tmp/help-live/help-base-url.txt`: help origin; contact uses `/contact`, Dashboard uses `/`.

To display those addresses locally, without printing credentials:

```bash
cd /home/shiyue1128/callgate-voice-risk-protocol
.venv/bin/python - <<'PY'
from pathlib import Path
device = Path('.test-tmp/device-live/ngrok-base-url.txt').read_text().strip()
help_origin = Path('.test-tmp/help-live/help-base-url.txt').read_text().strip()
print('Last verified device upload:', device + '/api/device-events')
print('Last verified contact:', help_origin + '/contact')
print('Last verified Dashboard:', help_origin + '/')
PY
```

These may rotate again. Before sharing, follow the recovery guide's **latest accepted forwarding event** lookup and verify that the actual contact HTML is served, not merely HTTP 200 from a tunnel provider page. Share the verified HTTPS URL and role credential separately through trusted channels; never commit either.

## Read-only morning health check

```bash
cd /home/shiyue1128/callgate-voice-risk-protocol
ss -ltnp '( sport = :8780 or sport = :8783 or sport = :4040 )'
.venv/bin/python - <<'PY'
import urllib.request, urllib.error
from pathlib import Path
checks = [
    ('local device HTML', 'http://127.0.0.1:8780/', 200),
    ('local contact HTML', 'http://127.0.0.1:8783/contact', 200),
    ('local help API without access', 'http://127.0.0.1:8783/api/help-requests', 401),
    ('saved public contact', Path('.test-tmp/help-live/help-base-url.txt').read_text().strip() + '/contact', 200),
]
for label, url, expected in checks:
    try:
        with urllib.request.urlopen(url, timeout=12) as response:
            status = response.status
            body = response.read()
            actual_contact = b'id="accept"' in body if 'contact' in label else True
    except urllib.error.HTTPError as error:
        status, actual_contact = error.code, False
    except OSError:
        print(label, 'unavailable; inspect locally, no automatic restart')
        continue
    print(label, status, 'PASS' if status == expected and (actual_contact or expected == 401) else 'inspect')
PY
```

This uses GET only. It submits no event or contact action. The existing `restart_reach_observed --verify-only` helper also replays an existing event as a duplicate; do not describe that helper as strictly read-only. It was not used for this overnight check.

## Recover only the failed component

Use [the exact component recovery instructions](REACH_DEMO_RECOVERY.md). First inspect ports, saved PIDs and actual command/cwd. Never use the initial device `start_local.py` to restart an existing runtime, delete tokens/databases, run the broad device stop script, or install a restart loop.

| Observation | Safe next action |
| --- | --- |
| Local help works, old public origin says No tunnel, SSH is alive | Extract the latest accepted forwarding origin and verify actual HTML plus role access; update only the private help origin file. Do not restart services or start a second tunnel. |
| Local help works and the matching SSH process is confirmed stopped | Use the documented one-attempt SSH command with the existing known-hosts file, no SSH identity/agent, forwarding only 8783. Record its actual PID and verified origin. |
| ngrok agent works and points exactly to 8780 | Leave it running. Never retarget it to payment services or request a replacement domain to work around an unrelated issue. |
| A local service is genuinely stopped | Reload that service's existing credentials and database using its documented recipe. Do not restart the other healthy service merely for convenience. |
| An App request returns 401 | Inspect the configured upload origin and raw device credential on the phone; 401 is not by itself a reason to restart a healthy backend. Preserve the same alarm's event ID. |

Sentry configuration must be in the **actual launching shell**; another Ubuntu window does not inherit it. Use the existing privacy-filtered implementation, not a replacement website snippet. For an intentionally scheduled restart of both services, the documented `scripts.restart_reach_observed --canonical-sentry-path` option preserves host/key/project while correcting the known extra cloud-ingest path. It is not a health-check command and must not be run against healthy services merely to view documentation. No restart was performed for this handoff.

## Shortest remaining manual acceptance

1. Refresh the verified help URL and open the actual contact page. Keep existing role credentials. Opening the page does not accept a request.
2. On the phone, confirm which supplied hardware-origin ID belongs to the teammate's actual button run. The two checked IDs are listed in the hardware receipt record; select that exact pending request. Do not substitute the accepted `local-test-http-…` event.
3. A human contact explicitly taps **I can help**. Record the displayed result; on an uncertain network outcome, inspect state before another tap. The assistant does not accept anything.
4. Read the Dashboard for the same ID and reconcile a single applied assigned-contact acceptance and audit time. A backend role action does not establish physical arrival or emergency dispatch.
5. In Sentry, inspect `help.response` near that actual acceptance time and open the actual Trace detail. The UI may display local time; distinguish it from UTC. Collect operation/HTTP status, trace/span IDs and measured duration only. Do not count human waiting as server latency or claim one cross-service distributed trace.

No new alarm is necessary to finish contact acceptance of the already recorded hardware-origin requests. If the teammate needs a fresh physical run instead, it is an explicit human-operated test, not something this handoff automatically triggers. Record firmware/App revision, phone/iOS, hardware alert identity and the exact backend event ID.

If authentication trouble recurs: the Swift uploader appends `api/device-events` to the configured **base origin**, and adds `Bearer` itself. The App token field needs the existing raw device token, without a `Bearer` prefix or quotes. In the inspected branch, saving a blank token keeps the old Keychain entry; it does not replace it. Check the actual runtime configuration with the credential owner, never publish it or regenerate it to hide a mismatch. A device-ID mismatch is a different backend response (403); a transport failure is not the same as HTTP 401. No specific cause of the earlier 401 has been established.

## Review, CI and merge order

- Sentry implementation [PR #1](https://github.com/Cyberchopin/reachguard/pull/1) and the original README/evidence [PR #2](https://github.com/Cyberchopin/reachguard/pull/2) are already merged on `main`. Do not reintroduce the old repository's independent history.
- The overnight documentation PR is based on current `main` and updates only documentation/evidence. It may be reviewed first; it does not require importing the iOS branch.
- The iOS draft [PR #3](https://github.com/Cyberchopin/reachguard/pull/3) uses the teammate's original `feat/reach-ios-gateway` commit unchanged. A merge-tree simulation found only the intended `ios/` additions and no conflicts against the checked main. Review may happen in parallel; a maintainer controls draft readiness and merging after the remaining acceptance/review.
- No PR is configured to auto-merge. No main or teammate branch is rewritten.

The checked main CI passed: **299 Python tests passed / 4 skipped**, **24 Node tests passed**, claims guard **51 registered / zero unresolved**. Sentry and README branch checks also passed. These are results of the existing Python/Node workflow, not Swift/Xcode/CoreBluetooth validation; optional SDK tests are not guaranteed by the workflow's install steps. Earlier dedicated local SDK/privacy tests are recorded separately in the Sentry acceptance. Read CI results with their actual coverage rather than treating green checks as hardware proof.

Outstanding human work: contact acceptance for a hardware-origin event, its Sentry response Trace, the actual hardware screenshot/log handoff, and maintainer PR review/merge. Do not invent missing evidence while the operators are offline.
