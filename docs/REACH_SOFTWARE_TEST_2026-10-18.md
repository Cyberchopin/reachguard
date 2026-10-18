# Reach software-only evidence rehearsal — 2026-10-18

Classification: **LOCAL_HTTP_PUBLIC_HTTPS_TEST_NOT_IPHONE_SHORTCUT_OR_BLE**.

The operator had no configured iPhone Shortcut available and explicitly requested a local HTTP upload instead. One new event was submitted from the operator's machine through the existing public HTTPS device endpoint using the existing device-only credential. No credential or temporary origin is included in this record. Contact acceptance is reserved for the human operator; the assistant did not submit a contact response.

## Event and upload evidence

- Event: `local-test-http-20261018T081156Z-78b3b9d5`.
- Device: `nano-01`; type: `help_request`; exactly three request fields.
- Client request window: `08:11:56.067801Z` → `08:11:56.225654Z`.
- Server-assigned receipt timestamp: `08:11:56.186178Z`.
- HTTP response: **201**, `status: received`, `intent_only: true`, same three fields plus the server receipt timestamp.
- Monotonic HTTPS client round trip: **156.118 ms**. This includes client/network/tunnel/server work and is not a server-only processing measurement.
- Help import timestamp: `08:11:56.277935Z`; initial state `recorded`, version 0, one applied source-record audit entry.
- The operator reported manually clicking **I can help** and observing **Contact accepted**. Read-only reconciliation confirmed acceptance at `08:14:10.541289Z`, current state `accepted`, version 1, and exactly two audit entries: source record and one applied contact acceptance. The actor matched the assigned contact; no actor identifier is published.
- Receipt-to-acceptance business elapsed time: **134.355111 seconds**. Import-to-acceptance: **134.263354 seconds**. Both include human waiting and must not be represented as server latency.

Times above are UTC on 2026-10-18. The difference between receipt and import timestamps is **91.757 ms**. These are business timestamps assigned in application code before their respective transactions finish, not commit-completion timestamps. The interval may include polling/scheduling and storage work; it is not a per-event server-latency benchmark.

## Screenshots and provenance

Evidence captures must show actual state read from the running service with actual role authentication, without mocked APIs, synthetic state substitution or automated acceptance. Only the chosen Local test's state card is captured, excluding role inputs, private origins, other requests and developer identity details. Browser viewport captures are not screenshots from an iPhone. The UI's displayed times use the browser's local timezone; the written timestamps above are UTC.

The included captures meet those conditions. Browser automation only connected using existing roles, selected the test by suffix and read rendered state. It did not invoke accept, unable or cancel. The before capture was made while the event was recorded; the after capture followed the operator's manual response. Images were captured directly using a DOM-element screenshot, with no post-capture editing, generated visual content or UI rewriting.

| File | Actual role/state | SHA256 |
| --- | --- | --- |
| [contact-recorded.png](assets/reach-software-test/contact-recorded.png) | Contact / recorded | `a1e2f9d41f6d6f1f34e179f737407cb250494020913996b6c351c3f168f46b8b` |
| [dashboard-accepted.png](assets/reach-software-test/dashboard-accepted.png) | Dashboard / accepted | `dd143f40c68f5cae239d7b56d3e635c97fbb9c0761aae8c8ba9c577881df89a8` |

The disabled cancellation control is the application's actual read-only Dashboard behavior.

## Sentry correlation boundary

### Actual operator-provided business logs

The operator pasted the following fields from Sentry Logs. These are actual business-operation records, not smoke-test records. The UI times were `Oct 18, 1:11:56.206 AM` and `1:11:56.204 AM`; interpreting the session's America/Los_Angeles timezone places them in the upload's UTC window. The pasted UI fields did not include a timezone suffix. [Structured, sanitized evidence](reach-software-test-2026-10-18.json) preserves the source distinction.

| Step | UTC time | Duration | Outcome / HTTP | Trace | Span |
| --- | --- | --- | --- | --- | --- |
| `device.upload` | `08:11:56.206Z` | **24.499 ms** | `ok` / `201` | `834071b8e04440bb806d78eb93449c3b` | `8d1b497d198e152d` |
| `device.persist` | `08:11:56.204Z` | **17.934 ms** | `ok` | Same trace | `a61bd36d4d64280d` |

These two logs directly share a trace ID and refer to distinct spans. Existing source instrumentation nests persistence inside upload processing. The persistence timing includes the instrumented context and commit/rollback, but connection creation occurs before that context. It is not a separate serial cost to add to the upload's 24.499 ms. The client's 156.118 ms is a different, wider HTTPS round-trip measurement; subtracting the server duration does not isolate pure network latency.

Exact event-ID correlation and the parent/child tree as displayed in Sentry were not independently exported here. No duration for `help.sync`, `help.persist`, `help.response`, `help.read` or `help.list` is inferred from these two records.

The operator also supplied `help.sync` logs at `08:16:54.891Z` (1.599 ms) and `08:17:57.234Z` (1.646 ms). Both are later than this event's import and acceptance. They show subsequent background sync visibility, not the first import of this event. They are retained separately as excluded observations in the JSON evidence and are not assigned as this event's processing latency.

| Stage | Business evidence | Sentry evidence available for this rehearsal |
| --- | --- | --- |
| Upload | Actual 201 response and persisted receipt | Operator-pasted upload log in the request window |
| Inbox persistence | Persisted inbox event | Operator-pasted persistence log sharing the upload trace ID |
| First help import | Matching help row and source audit timestamp | No matching import log/trace supplied; later sync observations excluded |
| Contact acceptance | Operator-confirmed click; exactly one applied assigned-contact audit entry | No matching `help.response` log/trace supplied at documentation time |
| Dashboard accepted | Actual read-only browser state and screenshot | No matching read/list log/trace supplied at documentation time |

The shared trace ID in two logs is directly observed. The corresponding business Trace detail tree was not independently exported or confirmed open here. General project visibility of Traces was confirmed in the earlier Sentry acceptance, but that is not substituted for this event's Trace detail. The table intentionally records evidence limits rather than inventing missing spans or timings.

Inspect upload candidates around `08:11:55Z`–`08:12:00Z` for `device.upload` and its `device.persist` span. Inspect `help.sync` / `help.persist` near the import timestamp. After the human submits a response, use its persisted audit time to inspect `help.response`, and then inspect read/list operations around the actual Dashboard observation.

Within one instrumented operation, generated trace/span IDs directly connect its logs and spans. Existing filters intentionally omit event IDs and do not propagate one distributed trace across services or later browser actions. A narrow time window therefore establishes temporal correlation, not an exact event-ID-to-trace join. Background sync may process zero or multiple events; ordinary page polling creates additional read/list traces. Do not present a smoke-test trace as this business event's trace.

Server operation durations exclude the person's time before clicking. The eventual import-to-acceptance or receipt-to-acceptance interval is business elapsed time, including human waiting. It must not be reported as server latency. Nested span durations must not be summed into an end-to-end benchmark.
