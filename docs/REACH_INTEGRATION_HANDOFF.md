# Reach integration handoff

## Main demo and ownership

Arduino button → BLE → foreground iPhone App → backend records help → trusted contact accepts or cannot help → Dashboard shows the actual state.

The teammate owns Arduino firmware, BLE and the Swift gateway. The backend owner owns event ingestion, contact responses and Dashboard. GATT UUIDs, characteristics, ACK bytes and binary framing must come from the teammate's firmware documentation; none are specified or guessed here.

## Actual progress

- Existing before this onsite integration: CallGate risk policy, processing consent, saved-contact challenge/signature verification and simulated actions. These remain a separate local demo, not prerequisites for help.
- Completed onsite: authenticated device inbox, persistent event idempotency, separate viewer access; HTTPS device upload tested; phone Shortcut HTTPS upload and real iPhone contact response completed according to the operator, with matching backend audit ([phone evidence](IPHONE_HELP_VERIFICATION_2026-10-17.md)). Local manual contact verification and simulated action completed (see [local evidence](LOCAL_MANUAL_VERIFICATION_2026-10-17.md)); this is not phone/hardware verification.
- Implemented and locally tested: independent help ingestion, scoped contact responses, owner cancellation, read-only Dashboard/status, persistent audit and serialized concurrent actions. No payment policy, CHALLENGED state, amount or six-digit payment code is required.
- Not verified: Arduino BLE button path, custom foreground Swift gateway, real emergency delivery or human identity enrollment.
- Help HTTPS is now available through a separate temporary localhost.run SSH tunnel to 8783, without changing the original device ngrok endpoint. Real public upload → browser contact acceptance → local Dashboard status was verified with a labeled local automated test. This does not establish iPhone/BLE completion. The earlier ngrok failure was the Free-plan custom-subdomain restriction, not a network timeout. See [phone response runbook](REACH_PHONE_HELP.md) for authorization and runtime address lookup.

## App upload contract (implemented)

The App accepts **backend URL and device credential at runtime**. Never hardcode a live URL, credential or test-role authority into Swift, firmware or this repository. Obtain current values through a separate local handoff. Device ID: `nano-01`; emergency event type: `help_request`.

```http
POST /api/device-events
Authorization: Bearer <device credential supplied locally>
Content-Type: application/json

{"event_id":"nano-01-unique-alarm-001","device_id":"nano-01","event_type":"help_request"}
```

`event_id`: 1–128 characters; `device_id`: 1–64; both permit letters, digits, underscore, dot, colon and hyphen. `event_type` permits `help_request` or legacy `verify_request`. Extra fields are rejected; maximum JSON body is 2048 bytes. No amount, contact approval or payment permission belongs in this payload.

| HTTP | Meaning |
| --- | --- |
| 201 | First durable receipt; `status: received` |
| 200 | Identical event retry; `status: duplicate`, original receipt retained |
| 401 | Missing/invalid credential or wrong role |
| 403 | Credential does not match device_id |
| 409 | Global event_id already used with different device/type |
| 413 / 422 | Body too large / invalid schema |

Successful responses include `event` (the three supplied fields plus server `received_at`) and `intent_only: true`. Upload success means backend receipt, **not** contact delivery or acceptance. For an uncertain network result, retry with backoff and the **same event_id for the same hardware alarm**. Generate a new ID only for a genuinely new alarm. BLE ACK means only that the phone received the message; it proves neither backend nor contact receipt.

Example using runtime shell variables; do not paste secrets into committed files:

```bash
curl --silent --show-error "$BACKEND_URL/api/device-events" \
  -H "Authorization: Bearer $DEVICE_TOKEN" \
  -H 'Content-Type: application/json' \
  --data '{"event_id":"local-test-replace-with-unique-id","device_id":"nano-01","event_type":"help_request"}'
```

## Independent help contract (implemented locally)

Help is a **separate service origin** from the device inbox. Device Bearer credentials cannot read help status, respond, or cancel. Help role credentials do not upload device events. All help APIs require the corresponding `Authorization: Bearer` role credential; there is no public credential/config endpoint.

| Endpoint | Permission / body |
| --- | --- |
| GET `/api/help-requests` | Scoped owner, contact or read-only dashboard; recent requests |
| GET `/api/help-requests/{event_id}` | Same scoped roles; state and audit history |
| POST `/api/help-requests/{event_id}/responses` | Assigned contact only; `{"action_id":"unique-response-id","response":"accept"}` or response `unable` |
| POST `/api/help-requests/{event_id}/cancel` | Assigned owner only; `{"action_id":"unique-cancel-id"}` |

Actions return 200 with action outcome, `duplicate` and current `request`. Invalid credentials return 401, wrong action role 403, absent/out-of-scope request 404, conflicting action ID or state transition 409, invalid body 422, oversized body 413; storage failure returns 503 without confirming an action. Retry the same uncertain action with the same action_id and content. Repeated identical actions return current state without adding a second audit action; a changed command/actor/event using that ID conflicts.

States: `recorded` → contact `accepted` or `unable_to_help`; the owner can change any non-cancelled state to `cancelled`. Cancellation is terminal. A response is allowed only while recorded. Transactions serialize races: cancel first rejects later acceptance; acceptance first is retained in history and a later owner cancellation becomes the final state. Competing accept/unable responses permit only the first. Rejected authorized attempts remain in the audit. Imported historic inbox help events remain historic events, not new deliveries.

Polling is implemented; push notifications, automatic escalation, dispatch, location, emergency-service delivery and device-credential status/cancel APIs are **proposed / not implemented**. Do not present them as connected capabilities. Acceptance means a scoped contact acknowledged responsibility, not that help arrived or a human identity was verified.

## Pages and private local handoff

Current local services (keep running during teammate testing):

- Device receipt display: `http://127.0.0.1:8780/` — separate viewer code.
- Help Dashboard: `http://127.0.0.1:8783/` — dashboard code for read-only viewing, owner code for cancellation.
- Help contact card: `http://127.0.0.1:8783/contact` — contact code only.
- Legacy local payment operator: `http://127.0.0.1:8781/fusion`; participant `http://127.0.0.1:8781/`; reviewer `http://127.0.0.1:8782/`. Payment services stay local.

Enter a role's code in its page access field. Existing ignored runtime directories hold the values: `.test-tmp/device-live/device.token` (App only), `viewer.token` (receipt display); `.test-tmp/help-live/contact.token`, `owner.token`, `dashboard.token` (distinct help roles). The operator must hand off only the required file's contents through a separate trusted channel on their machine. Never publish those files, private role links, runtime databases, screenshots containing live data, or ngrok configuration. This document contains paths, not credentials.

For a fresh local setup, start the inbox with `python -m scripts.start_device_events`, then `python -m scripts.start_help_demo` after confirming the inbox database path. Startup provisions random role identities/credentials once and retains existing runtime configuration. Do not start duplicate services on occupied ports. A future separate help HTTPS entry must point only to `http://127.0.0.1:8783`; the prepared `scripts.start_help_tunnel` refuses the existing device domain and makes one bounded attempt. Account/domain access must be configured locally, without committing its secrets.

## Evidence and remaining acceptance

Backend tests use synthetic isolated inboxes/databases, including permissions, persistent idempotency and cancellation/acceptance races. Browser evidence for the earlier ReachGuard payment UI uses explicitly synthetic previews; it does not validate the independent help mobile UI. The help pages have HTTP and JavaScript tests plus an actual Chromium mobile-viewport public acceptance check with no API interception; one real iPhone acceptance was operator-confirmed and reconciled with backend history; broader phone/browser, failure-path and hardware acceptance remains outstanding. Runtime credentials, databases and browser screenshots are excluded from publication. See the publication validation entry in BUILD_LOG.md for final check results.
