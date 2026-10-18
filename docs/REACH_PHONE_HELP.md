# Reach phone help response runbook

## Connection diagnosis and boundaries

The prior `ERR_NGROK_313` log explicitly identified a Free account attempting a custom subdomain. The old launcher invented a `reach-help-…ngrok.app` domain with `--url`. That is not a free randomly assigned endpoint. [Official ngrok limits](https://ngrok.com/docs/pricing-limits/free-plan-limits) allow one assigned development domain; custom names and generated domains require a paid plan. The existing assigned device domain remains in use. The launcher now requires an explicitly supplied, separately available domain instead of automatically repeating the failed configuration. No account upgrade, token readout or new ngrok retry was performed.

A separate free [localhost.run SSH tunnel](https://localhost.run/docs/) now forwards only to `127.0.0.1:8783`. [Its HTTPS termination](https://localhost.run/docs/security/) encrypts browser traffic and the SSH connection encrypts traffic back to the machine. It needs no additional account; the `nokey` SSH identity uses no private SSH key. Keep 8780 and its original ngrok process unchanged. Do not point this tunnel at fusion, participant or reviewer ports.

Public origins are runtime data, not checked-in configuration. The current help HTTPS origin is in ignored `.test-tmp/help-live/help-base-url.txt`; the original device origin remains in the running ngrok agent. Never use the localhost.run administration URL as the help origin. This session extracted the endpoint from its `v1.tcpip_forward.register.accepted` event and verified it with real HTTPS requests. Free domains are temporary and can change; the tunnel is not a persistent deployment or notification system.

## Shortest phone walkthrough

1. Keep the device App/Shortcut's existing backend URL, device ID `nano-01` and device credential unchanged. Send a new `help_request` with a new event_id. Retries of that same alarm reuse the ID.
2. On the contact's phone open **help HTTPS origin + `/contact`** in Safari. Only open the HTTPS address. Separately hand off the existing `.test-tmp/help-live/contact.token` contents through the agreed trusted channel. Enter it in **Contact access code**, then tap **Connect**. Do not put credentials in the URL query, screenshots or source files. Device/upload, owner and dashboard codes cannot substitute for contact access.
3. Select the new request under **Assigned requests**. New events deliberately do not replace the current selection. Check its time/device and, if necessary, event_id under **Developer details**. Tap **I can help** (the current button label). Opening the page alone does not accept anything. Wait for **Contact accepted**; if the connection fails, the result is not confirmed.
4. On the computer open `http://127.0.0.1:8783/`. Enter the separate `dashboard.token` in **Local role access code**, then **Connect**. Select that same request and observe **Contact accepted** plus its recorded history. This read-only role cannot cancel. Owner cancellation uses the distinct `owner.token`. The Dashboard polls every two seconds; it never invents contact receipt or acceptance.

The Dashboard is also available at the help HTTPS origin + `/`, with the same scoped role authentication. Device inbox display stays at `http://127.0.0.1:8780/` with its separate viewer code. Keep legacy payment services local.

## Verified evidence and limits

One new `local-test-help-https-…` event was sent through the unchanged public ngrok upload origin. First receipt 201, identical repeat 200, wrong-device attempt 403. Public help status without a credential or using device access returned 401. Owner contact-response and contact cancellation attempts returned 403. Contact/Dashboard HTML returned 200, payment-related routes 404.

Real Chromium at a 390×844 mobile viewport, using the real public help origin and actual role authentication (no intercepted APIs), selected only that labeled local test and clicked acceptance. Public response retry returned duplicate; the audit retained exactly one applied acceptance. The local Dashboard showed the same event accepted with cancellation disabled for display access. No page errors or horizontal overflow were observed. No live-data screenshots or credential values were printed. Private evidence is retained in `.test-tmp/help-live/public-check.json`.

This is **local automated HTTPS/browser testing, not an iPhone, BLE or hardware result**. A subsequent real phone Shortcut + iPhone contact acceptance was operator-confirmed and reconciled separately; see [observed phone evidence](IPHONE_HELP_VERIFICATION_2026-10-17.md). Arduino BLE and custom Swift gateway remain unverified. Acceptance acknowledges a scoped contact action, not arrival of help or verified human identity. No push delivery, dispatch, escalation or emergency-service guarantee is implemented.

## Runtime lifecycle

The separate SSH PID is in `.test-tmp/help-live/localhostrun.pid`; logs and its own known-hosts file are in that same private directory. To stop it, verify the PID's command is the localhost.run SSH command forwarding 8783, then terminate **only that PID**. Do not run the device stop.py or stop ngrok/8780. No automatic restart loop was installed.

For a later operator-controlled session, the essential forward is `ssh -R 80:127.0.0.1:8783 nokey@localhost.run`; use a private known-hosts file, `StrictHostKeyChecking=accept-new`, `BatchMode=yes`, no SSH agent/private identity, connection/forwarding failure limits and server keepalives. The current process was started once with those options. Use only the resulting HTTPS forwarding origin, not HTTP or an administration link. If the tunnel is lost, the page must report connection failure; do not claim delivery from stale state.

Full component recovery instructions and frozen-demo validation gaps: [REACH_DEMO_RECOVERY.md](REACH_DEMO_RECOVERY.md).
