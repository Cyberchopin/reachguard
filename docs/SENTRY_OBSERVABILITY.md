# Sentry observability

## Acceptance — 2026-10-18

**Accepted: the operator confirmed that the reachguard Sentry project displays both Logs and Traces.** This supersedes the earlier investigation's pending UI-receipt status. The confirmation was received in this session; the exact first-visible/indexing time was not captured. Page visibility is operator-confirmed, not independently inspected through authenticated Sentry access by the agent.

Evidence chain:

- The operator's shell ran the corrected probe at `2026-10-18T07:44:20Z`: one smoke transaction and one smoke log each received HTTP 200, with no recorded network exceptions, losses or rate limiting; probe queues were empty after flush.
- The explicit corrected-path restart loaded the existing Tracing/Logs implementation and privacy filters into service PIDs 6125 (8780) and 6138 (8783). Read-only inspection confirmed both inherited canonical ingest paths and the same project ID. Runtime business credentials, databases, ports and tunnel configuration were retained.
- Local and public business checks passed, including role access, device-role isolation, status reads and exact duplicate event upload. No new help request or contact action was performed for this observability acceptance.
- At `2026-10-18T07:45:01Z`, a separate probe using PID 6138's inherited configuration, without probe-side path correction, again received HTTP 200 for both Trace and Log. Its queues were empty, with no recorded network exceptions or losses. This verifies the inherited configuration's delivery path; it is not a direct inspection of the live service's in-memory SDK queues.
- The operator subsequently confirmed both data types visible in Sentry. The previous fixed query window ended at `07:43:36Z` and excluded the two later probes.

Scope: actual smoke-test delivery and operator-confirmed Sentry UI visibility, plus the listed business availability checks. This does not independently establish Sentry receipt of every business operation, a new contact-response trace, the Arduino/BLE/Swift path, an incident fixed through telemetry, or a performance improvement. Related isolated regression/privacy/business suite: **37 passed**. No service restart, additional telemetry send, business action or feature change was performed while recording this acceptance. No DSN, credential or private URL is included here.

The sections below retain the chronological audit and troubleshooting evidence; statements that deployment or UI verification were pending describe those earlier checkpoints.

## Reach service audit and new integration (2026-10-17)

The running 8780/8783 processes were inspected without restarting: neither has `CALLGATE_SENTRY_DSN` or `SENTRY_DSN`. The original virtual environment had no SDK. Neither Reach launcher previously initialized Sentry. The older hooks below are for the separate simulator and use `capture_message`, not Sentry Logs. They do not establish Reach telemetry.

New source integration: `callgate/reach_observability.py`, initialized by the device `from_env` factory and the help launcher. It uses actual SDK transactions/spans and `sentry_sdk.logger.info`, with `enable_logs=True`. SDK 2.72.0 was installed for in-memory envelope tests; the optional dependency now requires >=2.72,<3. Current live processes retain their old imports/environment; these changes are **implemented, tested locally, not deployed**. No actual Sentry project receipt or performance improvement is claimed.

| Operation | Trace / Logs coverage |
| --- | --- |
| `device.upload` | HTTP receipt, validation/auth outcome via numeric status |
| `device.persist` | SQLite context including commit/rollback; durable receipt and duplicate handling |
| `help.sync` | Read inbox and import into help state; background iterations also have root transactions |
| `help.persist` | Help SQLite context including commit/rollback, import and response audit/state persistence |
| `help.response`, `help.cancel` | Role-authorized HTTP action, numeric HTTP outcome |
| `help.list`, `help.read` | Scoped list and individual status reads |

Logs carry only a fixed operation name, outcome, measured duration, optional HTTP status and generated trace/span correlation. Traces use static operation names. There is no event/device/actor/action ID, credential, URL/query, request/response body, SQL text, database path, user context, breadcrumb or exception text. Default and automatic SDK integrations are disabled; arbitrary logs and error events are dropped. The transaction filter reconstructs an allowlist while retaining trace IDs (the older simulator filter removes trace context and is not reused). No incoming trace headers or baggage are accepted. A transaction and its logs can be correlated within a process; the separate inbox-to-help polling boundary does **not** currently form one distributed trace.

### Configure locally, without exposing the DSN

1. In Sentry, create/select a Python backend project and copy its project DSN. No Sentry auth token is needed for runtime ingestion. Confirm Traces and Logs are available in that project.
2. In the Ubuntu shell that will launch each service, enter the DSN without terminal echo or a literal shell-history entry:

```bash
cd /home/shiyue1128/callgate-voice-risk-protocol
read -rsp 'Sentry project DSN: ' CALLGATE_SENTRY_DSN
printf '\n'
export CALLGATE_SENTRY_DSN
export CALLGATE_SENTRY_TRACES_SAMPLE_RATE=1.0
```

This config is shell-local; it is not automatically loaded from `.env`. Do not put it in Swift, URLs, logs or committed files. Set it separately in each launch shell; both services need it to cover both halves of the flow. Keep the SDK installed in the existing `.venv` (`uv pip install --python .venv/bin/python 'sentry-sdk>=2.72,<3'`).

3. Do **not** run another copy on occupied ports. At the next planned service restart, follow [the existing recovery recipes](REACH_DEMO_RECOVERY.md) from a shell with those exports. Retain all existing role files and databases. The device recovery recipe passes the environment to the child; the help launcher inherits it. Healthy ngrok/SSH tunnels do not need restarting. No restart was performed for this audit.
4. After rollout, rehearse a clearly identified test alarm using the same three-field device contract, accept through the contact page and read Dashboard state. In Sentry, verify `device.upload` / `device.persist`, `help.sync` / `help.persist`, `help.response`, `help.read` / `help.list` transactions and `reach.operation` Logs. Open a log's trace ID to check correlation. Check both HTTP outcome and durable application state; a log alone does not prove commit or contact acceptance. Do not simulate a production incident to make a demo result.
5. Only after observing real project ingestion record its timestamp and evidence. If no records arrive, check DSN presence in the **service process**, SDK version, sampling, project selection and network access without printing configuration. Project-side delivery remains unverified until then.

### Operator restart from the configured shell (2026-10-18)

### Actual delivery investigation (2026-10-18, UTC 07:40–07:42)

The user confirmed reachguard project ID matches both service DSNs. SDK 2.72.0 is installed; the same configuration function enables Logs and installs the existing filters. Merely observing that initialization was not sufficient: a separate diagnostic process privately copied each service's DSN/network environment and reproduced actual HTTP delivery. This does not inspect the live Python workers' in-memory queues or flush those workers.

Both DSNs contained four extra path-prefix segments ahead of the numeric project ID. With the original routing, both transaction and log envelopes received **HTTP 404**, HTML responses. No connection exception, rate-limit header, Retry-After or Sentry error header was observed. Flush emptied the **probe's** worker/log queues; the SDK recorded lost transaction/log items. Its `network_error` loss label here does not mean DNS or connection failure: HTTP 404 was directly observed.

The diagnostic then corrected only its own in-memory cloud-ingest path, retaining the host, key and project ID. Both transaction and log envelopes received **HTTP 200**, JSON responses, with no losses or network exceptions; probe queues were empty after flush. The latest recorded smoke timestamp was `2026-10-18T07:42:08Z`. The fixed log label is `reach.step:observability.smoke_test`; log body remains `reach.operation`. Trace correlation and timestamp were present, and server/local clock difference was about 0.3 seconds. HTTP acceptance is established for that probe; project UI indexing/visibility is not independently established. No business API, new help request or contact action was used. The running service environments remain unchanged until an explicit restart.

In the second shell with exported Sentry configuration, preflight one smoke test and then restart with corrected routing:

```bash
cd /home/shiyue1128/callgate-voice-risk-protocol
set +x
export CALLGATE_SENTRY_DSN CALLGATE_SENTRY_TRACES_SAMPLE_RATE
.venv/bin/python -m scripts.diagnose_reach_sentry --canonical-ingest-path &&
  .venv/bin/python -m scripts.restart_reach_observed --canonical-sentry-path
```

The probe exits unsuccessfully unless both Trace and Log receive 2xx, so failure does not proceed to restart. The explicit correction only permits standard Sentry cloud-ingest hosts. It preserves credentials and does not print the DSN. The restart passes the corrected path to child processes; it does not rewrite the parent shell's variable. Future restarts from that shell must retain the explicit option or use a correctly recopied project DSN. Restarting without the option now rejects unexpected cloud path prefixes before stopping services. Runtime credentials, databases and tunnels are retained. Regression/privacy/business suite: **37 passed**.

To check a restarted process's actual inherited configuration without assuming shell inheritance, use `.venv/bin/python -m scripts.diagnose_reach_sentry --from-service help-live` (or `device-live`). This sends one explicitly labelled smoke log/transaction and prints sanitized HTTP outcomes, SDK queue/loss data and generated trace metadata, never the DSN. This is still a separate probe, not an introspection endpoint in the service. In reachguard Logs select the last hour/all environments, clear other filters and search `reach.step:observability.smoke_test`; check the matching trace. If the UI still shows no first log after accepted envelopes, inspect project Stats for accepted/filtered/rejected logs and ingestion quotas. Reading those project-side records requires account access; DSN alone does not establish them.

### Normal restart and verification

Observed startup-check correction: the help launcher reserves/listens on its socket **before** configuring telemetry. The first restart checker treated a listening socket as a reason to immediately require the initialization log marker. This could report `telemetry not confirmed` while initialization was still progressing. The reported process remained alive and subsequently logged successful SDK initialization. No further restart was needed. The checker now polls for all three conditions: expected PID owns the listener, the new log segment contains the initialization marker, and local HTTP returns 200. A missing marker during startup is pending until the readiness deadline, not an immediate failure. Existing privacy filters are unchanged.

After the reported restart, both original replacement processes had their Sentry variables present and successful initialization markers, with no traceback marker found in their service logs. Local/public HTML, existing role access, device-role isolation, status reads and exact duplicate upload checks passed; saved public origins were unchanged. No new help request or contact response was performed. Regression and privacy/business tests: **36 passed**. This establishes local SDK initialization and business availability, not Sentry-side receipt. Verification output now omits public/private runtime addresses as well as credentials.

When the second Ubuntu shell already contains the DSN and sampling rate, use:

```bash
cd /home/shiyue1128/callgate-voice-risk-protocol
set +x
export CALLGATE_SENTRY_DSN CALLGATE_SENTRY_TRACES_SAMPLE_RATE
.venv/bin/python -m scripts.restart_reach_observed
```

This is an explicit restart of 8780 and 8783, not an initial provisioning command. The script checks existing runtime files, matching role files, DSN syntax, installed SDK and sampling before stopping anything. It locks against concurrent invocations and checks listener PID, launch module and working directory. It uses graceful SIGTERM, waits for the old process and port to close, and never force-kills or retries a failed start. Each new service must listen on its original port and write the privacy-safe telemetry-enabled startup marker before the script proceeds. Logs remain in each original runtime `service.log`; both children inherit the shell's Sentry configuration. No DSN value is displayed.

Healthy tunnels are left running. The script automatically checks local and public HTML, role access, device-credential isolation, status reads and exact duplicate upload of an existing help event; it does not create an alarm or accept a request. Only successfully verified public origins are saved. A tunnel failure is reported separately after local checks, and does not mean a service restart failed. Inspect state before rerunning a failed restart command.

For subsequent checks without another restart (no DSN needed in the checking shell):

```bash
.venv/bin/python -m scripts.restart_reach_observed --verify-only
```

The startup marker confirms local initialization, not delivery to Sentry. Select the configured project, the last 15 minutes, and all environments in Sentry. In Explore Logs search `reach.step:device.upload`, then check `device.persist`, `help.sync`, `help.persist`, `help.read` and `help.list`. In Traces search `span.op:reach`; open the log's trace link to check within-process correlation. To exercise contact response after restart, make one clearly identified new test alarm, accept through the existing contact page, confirm the Dashboard's actual state, and look for `reach.step:help.response`. Do not reuse an already accepted alarm as new evidence. Error events are deliberately dropped, so an empty Issues page is not proof of missing Tracing/Logs. Live Sentry receipt is only verified when records are actually visible in the project.

### Isolated test details

`tests/test_reach_observability.py` captures actual SDK envelopes in an in-memory Transport, with a non-routable test DSN. It exercises upload/retry, import, contact acceptance, status reads, access failures and a deliberately injected test-only exception. It asserts both transaction and log items, span/log correlation, persistence spans, and absence of private canaries in the serialized envelopes. It never uses live credentials/databases or sends to a Sentry project.

```bash
.venv/bin/python -m pytest tests/test_reach_observability.py tests/test_device_events.py tests/test_help_requests.py tests/test_telemetry_privacy.py -q -p no:cacheprovider
```

Observed result on 2026-10-17: **30 passed** with SDK 2.72.0. These are isolated test results, not production telemetry or latency measurements. Live read-only/rejected-request checks confirmed the original service PIDs remain running, the upload model rejects `alert_type` with 422, and device credentials receive 401 for help list, detail and cancellation. The free help tunnel rotated during this audit; its latest accepted origin was verified with HTML and role authentication and saved only in the ignored runtime file, without restarting either service or SSH.

Official API references: [Python Logs](https://docs.sentry.io/platforms/python/logs/), [SDK configuration and callbacks](https://getsentry.github.io/sentry-python/api.html). No Session Replay, profiling or new product behavior was added.

## Legacy simulator integration

Implemented: optional privacy-bounded hooks for the local simulator. Not implemented: a committed DSN, public production telemetry, Session Replay setup, or proof that an external Sentry project received events.

## What is instrumented

The broker emits trace/log records around these demo steps:

| Step | Purpose | Sensitive fields deliberately omitted |
|---|---|---|
| `transcript_to_evidence` | Measure local parsing and policy update time | Transcript text |
| `policy_decision` | Record the resulting state name | Transcript text and caller content |
| `challenge_request` | Measure challenge creation | Amount, destination, contact identity and challenge code |
| `reviewer_decision` | Measure signed reviewer completion | Reviewer identity, challenge response and operation details |
| `gateway_refused` | Record direct protected-action refusal | Amount and destination |

Only `session_hash`, state names, event types, durations, outcome status and error codes are intended to leave the process.

## Runtime configuration

Set `CALLGATE_SENTRY_DSN` in the process environment to enable Sentry. The DSN is not read from code or committed files.

```bash
CALLGATE_SENTRY_DSN=... python -m scripts.start_review_demo
```

If `sentry-sdk` is not installed or the DSN is absent, the demo still runs and no outbound Sentry event is sent.

## Privacy guard

`callgate.sentry_observability` sets `send_default_pii=False` and uses event filters before Sentry receives events. The tests use a fake transport and assert that a sensitive transcript, a plain amount, a destination and contact-like fields are absent from emitted records.

Run:

```bash
python -m pytest tests/test_telemetry_privacy.py -q -p no:cacheprovider
```

## Honest demo note

This repository does not yet contain a real "observability changed the implementation" record from a live Sentry trace. If that happens during the hackathon, record the timestamp, observed trace/log, code change and before/after measured output in `BUILD_LOG.md`. If it does not happen, say so.
