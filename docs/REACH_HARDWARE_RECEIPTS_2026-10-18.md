# Hardware-origin receipt reconciliation — 2026-10-18

## Provenance and limits

The operator relayed a teammate report that real button → BLE → Swift → backend upload passed and that an App screenshot shows **Medical / Recorded by backend (201)**. This supplies reported hardware/App provenance. The screenshot file itself was not supplied to or inspected by the agent; the existing software-test README screenshots are not relabelled as hardware evidence.

The agent independently queried the existing inbox and help SQLite databases in read-only mode for the two supplied event IDs. No event, contact response, cancellation, restart or credential change was performed. The structured [receipt evidence](reach-hardware-receipts-2026-10-18.json) is sanitized and omits private origins, credentials and contact identity values.

## Directly checked backend snapshot

Checked at **2026-10-18 08:38:39.626746 UTC**.

| Event ID | Device / event type | Receipt UTC | Import UTC | Current help state | Applied acceptances |
| --- | --- | --- | --- | --- | --- |
| `nano-01-87a65e40-14e8-47ac-8dc2-ceaed18e4078` | `nano-01` / `help_request` | `08:32:52.567910` | `08:32:53.170377` | `recorded`, version 0 | 0 |
| `nano-01-c41ea862-09b5-4b2b-8379-8275b2e99fdb` | `nano-01` / `help_request` | `08:33:39.743051` | `08:33:40.458903` | `recorded`, version 0 | 0 |

Each event has exactly one applied source-record audit entry in that snapshot. Neither has a contact acceptance, unable response or cancellation. These are timestamped observations, not a promise that a later human action cannot change state.

The database confirms persistence and help-request import, not the BLE sender or original HTTP response status. The App's **201** and hardware path are teammate/operator-reported. A previous report of 401 is historical; the later successful report and matching receipts supersede it as the latest upload outcome. No specific cause or code fix for the earlier 401 is established.

**Medical is an App label, not a backend alert type.** The backend stores `help_request` for both IDs and does not implement `alert_type`. The records do not establish medical dispatch, emergency-service delivery or arrival of help.

## Remaining acceptance

- A human selects one of these exact pending IDs and explicitly chooses **I can help**; the assistant must not do so.
- Reconcile the same ID to one applied assigned-contact acceptance and the read-only Dashboard state. Do not substitute the already accepted local HTTP test.
- Record phone/iOS and firmware/App revisions alongside the teammate's actual hardware screenshot/log evidence when available. Do not publish credentials or temporary origins.
- Verify any claimed contact-response Sentry Trace in its actual detail view. Upload/persistence Trace confirmation from the local HTTP rehearsal is separate evidence and does not establish tracing for these hardware-origin events.
