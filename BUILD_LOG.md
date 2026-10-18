# CallGate v2 build disclosure

- User request date: 2026-09-08, America/Los_Angeles.
- Research baseline: `16c469ae78f22f06df757595b8b36edd9359086e` (original remote main).
- Working branch: `callgate-v2/phase-1`.
- Scope change: user explicitly requested implementation now for AssemblyAI and AI Infra, with later reuse. Earlier LA Hacks research-only timing is historical, not an instruction to delay this work.
- AI-assisted implementation: Codex implemented the files in `callgate/`, `tests/`, `scripts/`, `scambench/` and v2 documentation in this working session. No third-party implementation source was copied.
- Existing work: all original research documents. New work: English rules baseline, strict schemas, revision-aware state and timeline, advisory Guardian, REST/transcript/audio WebSocket adapters, AssemblyAI v3 normalization, WAV streaming client, tests, synthetic development corpus and evaluator.
- Tests: see `scambench/results.json` and `scambench/test-results.xml`; these are local measurements, not competition or production results.
- External service: AssemblyAI adapter written against official streaming documentation; no live credentialed audio call was run.
- Not built: semantic LLM extractor, speaker role mapping, deepfake model, independent verifier, capability tokens, signed receipts, real payment/phone controls, production auth/deployment.
- Later event disclosure: list this entire baseline as pre-existing when applicable. Do not claim it was built during a future event. Keep event-specific deltas in separate branches and verify sponsor/eligibility rules at submission time.

## Subsequent live provider smoke test

After the user configured the local key and requested continuation, two synthetic English WAVs were streamed at realtime pace through the actual AssemblyAI v3 service and existing Conversation engine. See timestamped `scambench/live-scam.json` and `scambench/live-benign.json`.

- Scam sample: bank claim → immediate money request → secrecy; observed UNVERIFIED → CHALLENGED → COOLING_OFF, score 80, Guardian PAUSE.
- Benign sample: lunch appointment; remained UNVERIFIED, score 0, Guardian LISTEN.
- The synthetic audio was generated using gTTS 2.5.4 and converted using miniaudio 1.71 as test preparation, not product dependencies. The application credential was sent only to AssemblyAI in its authorization header. No microphone or real call was captured.
- Added `scripts/live_smoke.py` for explicit WAV-to-provider-to-engine smoke runs. All 18 existing tests still passed afterward. The local click dependency was resolved to 8.1.8 by the audio preparation tooling and is reflected in the lock file.
- This supersedes the earlier 'no live credentialed audio call' status for these two samples only. It does not establish real-call accuracy, device capture, REST/audio WebSocket end-to-end behavior, or production reliability.

## Local microphone test page

Added a minimal local page with explicit Start/Stop, microphone level, revision-aware transcript, Chinese Guardian messages and state transition list. Added a `.env`-aware launcher, same-origin browser WebSocket checks and restricted static assets. The server returned HTTP 200 at `http://127.0.0.1:8765/`; 20 Python tests passed and both browser JavaScript files passed syntax checks. The two additional tests cover the demo route/origin rejection and the local audio WebSocket pipeline with a simulated provider. Browser/device capture is awaiting user testing; no claim is made that a browser tab or permission popup is visible on the user's screen.

## User microphone feedback and bounded rule repair

The user subsequently reported successful microphone transcripts for the money+secrecy sample (70, COOLING_OFF) and benign lunch sample (0, UNVERIFIED). They also reported an exact transcript of "Move your savings into the secure holding wallet." with score 0, confirming the known paraphrase false negative in the live user flow.

`rules-en-v2` adds a bounded asset-relocation request grammar, covering move/shift/relocate/transfer/send/deposit + savings/funds/balance/etc. + wallet/account. Sentence/request-prefix matching avoids several first-person plans, conditional discussions and negated warnings. This is a rule expansion, not a semantic model, and unfamiliar wording/quotations still need further work. Fourteen additional tests cover variations, benign discussion, negation and cross-turn secrecy; all 34 tests passed. The unchanged 12-case development corpus now has 11 state matches; the quoted-warning false positive remains explicitly reported in `scambench/results-rules-en-v2.json`. The original result file is retained for comparison.

## Open-source reuse integration, 2026-09-08

14 upstream checkouts pinned in docs/upstreams.json. Integrated MIT Silero model and Pipecat 1.8.1 processor boundary; see docs/REUSE_PLAN.md and THIRD_PARTY.md. Optional sensor inference failure preserves raw STT input. 39 tests passed. Real provider/local WebSocket smoke completed with 106 sensor observations and COOLING_OFF decision. Demo restarted with CALLGATE_VAD=silero. Hosted forks remain blocked by expired CLI authentication and signed-out browser; no forks claimed created.

## Context regression update

Extractor rules-en-v3 narrowly recognizes explicit hypothetical scammer examples within one sentence. Contrast and sentence boundaries preserve subsequent action requests; quotes alone do not suppress detection. Responses expose educational_context_heuristic uncertainty and never authorize an action. Eight paired boundary tests added; full suite 47 passed. Original unchanged 12-case development corpus now 12/12 (results-v3.json). This is same-author development validation, not held-out accuracy. Broader paraphrases, punctuation-free speech and genuine semantic attribution remain open.

## Final-product local increment — 2026-10-05 America/Los_Angeles

User requested immediate final-product development rather than research-only preparation. This work was built now, not during a future event. No external PR, push, deployment or message was made.

Baseline inspected: `e72e85a22a6ec0ef19f0a9ee07b4093eb8af7753`. `git log -10 --oneline` read before changes. `docs/PROJECT_TRUTH.md` and FEATURE_LEDGER did not exist in this snapshot; created with explicit seed verification. Prior assistant ZIP-only assessment was stale.

### Implemented

- Bounded bilingual text extractor in new `callgate/safety_policy.py`; archived English `engine.py` unchanged.
- Live ratchet: historical safety categories and risk restrictions cannot weaken under revision, order changes or duplicate segments. Current evidence remains revision-aware.
- Connected reviewer workflow uses the new live policy; Chinese/mixed text selector exposed in participant UI. Mandarin streaming ASR is not claimed validated.
- Direct simulator operation endpoint returns HTTP 403 / `POLICY_PROOF_REQUIRED` without granting any action.
- Reviewer denial, expired pending confirmation or exhausted guesses latches authorization refusal for the session. Amount/destination changes cannot bypass it. Explicit new-session reset remains a demo boundary, not production identity enforcement.
- Offline counterfactual-plus-valid-approval rehearsal; generated local keys explicitly not independent human verification.
- PROJECT_TRUTH, CLAIMS, frozen-evidence hashes, claims CI gate, prospective blind inputs, story/privacy/runbook assets.

### Test-first evidence

New claims tests initially: 5 failed (checker absent), then passed after implementation.
New bilingual/ratchet fixtures initially: 10 failed (module absent), then passed.
Denial retry and direct-action tests initially: 2 failed (retry allowed / route missing), then passed.
Denial scope-change and expiry tests initially: 2 failed (new authorization allowed), then passed.
The old pending-capacity regression explicitly creates new consented sessions after timeout now; it no longer treats silent renewal of an expired session as desired behavior.

### Commands and actual outputs

Environment: isolated Python environment; installed repository core and verification locks and `requirements-safety.txt`. Optional Pipecat/Silero packages not installed. No provider credentials used.

- Original suite: `python -m pytest -q -p no:cacheprovider`: 181 passed / 184 collected, 3 skipped; not a reproduction of all historical 184 passes.
- Final suite: `python -m pytest -q -p no:cacheprovider --junitxml=...`: 206 passed / 209 collected, 3 skipped, 0 failures, 0 errors; 2 deprecation warnings.
- `node --test tests/review_ui.test.cjs`: 3 passed / 3 tests, 0 failures.
- `node --check callgate/demo/review-ui.js`: exit zero.
- Property test with `--hypothesis-show-statistics`: 1000 passing / 1000 valid generated examples, 0 failing; 83 invalid generation cases discarded. This is not 1000 independent real calls.
- `python scripts/check_claims.py`: registered=31, unresolved_or_inconsistent=0. Initial pending bindings failed closed before they were bound. README performance values were not changed to make them pass.
- `python evaluation_v2/verify_inputs.py`: 90 scripts, 30 correlated scenario families; English/Mandarin/mixed each 30; 10 slices each 9. No CallGate predictions run on these inputs.
- `python -m scripts.proof_demo`: forced empty detector yielded UNVERIFIED but direct action returned actual HTTP 403 with `POLICY_PROOF_REQUIRED`; fresh valid signed simulation completed. Generated reviewer key, no real financial action.
- `python -m evaluation_v1.evaluate_pilot render`: exit zero; frozen CallGate recall 1/8 and baseline recall 2/8 unchanged. Renderer-only line-ending changes restored to original CRLF after whitespace-insensitive diff confirmed equal content.
- `git diff --check`: no whitespace errors.

Raw archive SHA-256 remains `32155007486e09295ffb05f3f0081a36b4133e3146e5da4e017e98581f4722dd`. Label/freeze/archive hashes are separately pinned in `docs/immutable-evidence.json`. No v1 labels, first-run predictions or raw archive hashes were modified.

### Still incomplete

- Independently enrolled claimed-identity-bound contacts and remote dual-device delivery; current role separation does not prevent one person controlling both roles.
- Production tool integration, issuer/contact revocation, trusted HTTPS deployment, data TTL guarantees.
- Independent annotations; population-level legitimate-request utility and warning coverage of new live rules.
- Real Mandarin streaming verification; surgical audio generation and measured ASR perturbations.
- Four-baseline joint safety/utility study with intervals and latency; cannot report it before actual runs and reviewed labels.
- Browser visual QA and prerecorded offline video on the user's devices.

Next work must start from the current checked-out code and this log, not the September research ZIP. Do not call this increment an award-ready complete deployment.

## 2026-10-06 — PR preparation requested by owner

Owner authorized publishing yesterday's local increment as a branch and pull request. GitHub repository metadata resolves the former repository name to `Cyberchopin/callgate-voice-risk-protocol`; remote main remains `e72e85a22a6ec0ef19f0a9ee07b4093eb8af7753`.

Recreated the missing virtual-environment interpreter and reran checks against the preserved code:
- `python -m pytest -q -p no:cacheprovider`: 206 passed / 209 collected, 3 skipped, 2 deprecation warnings.
- `node --test tests/review_ui.test.cjs`: 3 passed / 3 tests; JavaScript syntax check passed.
- `python scripts/check_claims.py`: registered=31, unresolved_or_inconsistent=0.
- `python evaluation_v2/verify_inputs.py`: 90 scripts / 30 correlated families; independent annotation pending, no predictions run.
- `python -m scripts.proof_demo`: direct action returned 403 POLICY_PROOF_REQUIRED with detector forced empty; separately signed simulated approval completed; no real action.
- `python -m callgate.bench`: 25 / 25 development state fixtures passed; this is the existing English development smoke corpus, not a new accuracy study.
- `git diff --check`: passed.

The incomplete items above remain unchanged. This entry records local checks, not remote CI results or a merged PR.

## 2026-10-06 — Claimed identity bound to saved contact

Owner reported squash merge and requested continued development. Fetched main and confirmed merge commit `1882e3d`; created `feat/claimed-contact-verification` from main. Read PROJECT_TRUTH, FEATURE_LEDGER, the latest BUILD_LOG and git history. Historical pending-PR descriptions now have an explicit merge-status correction; no frozen pilot facts were changed.

Implemented trusted-startup contact directory, identity-to-reviewer routing, recorded same-origin rejection, duplicate signing-key rejection, and identity-bound operation commitment. The launcher provisions one synthetic saved identity; participant selection and reviewer display are wired to the existing HTTP flow. Reviewer capability and signer endpoints check the selected addressee. Expired requests are cleared on status/pending reads and session authorization refusal is visible in the UI.

Test-first evidence: the new contact test module initially failed collection because `callgate.contacts` did not exist. The timeout/status regression then failed because pending remained true after expiry. Both were implemented and verified. The existing spawned-process integration initially failed after changing the launcher signature; updated it to exercise required saved-identity selection and actual identity-bound approval rather than retaining legacy launcher behavior.

Actual final checks:
- `python -m pytest -q -p no:cacheprovider`: 225 passed / 228 collected, 3 optional integration skips, 2 deprecation warnings. This includes the spawned-process loopback integration; no external services used.
- `node --test tests/review_ui.test.cjs`: 3 passed / 3 tests; `node --check callgate/demo/review-ui.js` passed.
- `python scripts/check_claims.py`: registered=31, unresolved_or_inconsistent=0.
- `python evaluation_v2/verify_inputs.py`: 90 scripts / 30 correlated families; no predictions, independent annotation pending.
- `git diff --check`: passed.

Remaining: independent human enrollment, real remote dual-device delivery, multiple-contact delivery fan-out, identity-provider authentication/revocation, persistent denial across restart, real tools, new joint evaluation, Mandarin streaming validation and browser/device visual rehearsal. Credential origins are trusted configuration records, not proof of physical people. One operator holding both launcher role URLs can still approve. The code rejects recorded same-origin credentials; it does not solve that broader problem.

## 2026-10-07 — Multiple scoped saved-contact reviewer processes

Owner requested continued work and a new PR. Fetched main: previous contact PR squash-merged as `6855522`; its PR-triggered workflow completed successfully (observed through GitHub). Created `feat/multiple-contact-routes` from that main snapshot; read current truth/ledger/build log and git history.

Implemented repeated `--contact-identity` provisioning for distinct synthetic saved contacts. Each reviewer process generates its own private signing key; only public keys reach the broker. Broker bearer authentication now resolves a trusted reviewer principal from distinct per-reviewer capabilities, filters pending requests to that principal and refuses decisions addressed to another contact. Participant credentials, unknown capabilities, duplicate tokens, missing/invalid route credentials and unscoped multi-contact configuration are rejected. Single-contact startup and legacy programmatic credential configuration remain supported.

Launcher validates distinct identifiers and bounded local capacity before starting services, prints labeled reviewer entries, uses automatic additional loopback ports, and stops all children if any process ends. Switching claimed identity invalidates the previous pending request; no failover to an unrelated contact is introduced. README, contact guide, truth/ledger and failure runbook updated.

Test-first evidence: new tests initially failed collection because `_contact_ids` did not exist. Added capability/configuration regressions and actual HTTP integration through a broker and separate family/bank reviewer processes. Integration checks cross-contact invisibility, wrong entry capability, wrong addressee, identity switching, signed simulated completion and replay refusal. A malformed insertion in the new test was caught during collection and corrected before the final checks.

Final actual checks:
- `python -m pytest -q -p no:cacheprovider`: 240 passed / 243 collected, 3 optional integration skips, 2 deprecation warnings.
- `node --test tests/review_ui.test.cjs`: 3 passed / 3 tests; JavaScript syntax check passed.
- `python scripts/check_claims.py`: registered=31, unresolved_or_inconsistent=0.
- `python evaluation_v2/verify_inputs.py`: 90 scripts / 30 correlated families, manifests/schema verified, no CallGate predictions run.
- Actual launcher CLI smoke with separate saved-family/saved-bank flags and automatic ports: two correctly labeled reviewer entries and authenticated broker directory HTTP response verified. Generated capability values were omitted from output. Initial smoke harness used buffered line reading with select and timed out; corrected the harness to read bytes and reran successfully. All spawned smoke processes were stopped.
- `git diff --check`: passed.

Remaining: remote device/phone delivery, independently verified humans, identity-provider authentication and revocation, persistent denial/replay lifecycle across restart, production integrations, independent annotations/new joint safety-utility results, Mandarin streaming validation and visual device rehearsal. Multi-contact routing here is local and synthetic; one operator may still control every role entry. No frozen pilot labels, results or archive hashes changed.

## 2026-10-07 — Checkout skin and privacy-bounded Sentry hooks

Owner supplied sponsor-track guidance: keep Visa alignment as a thin checkout skin, and replace generic OpenTelemetry work with Sentry-style tracing/logging guarded by privacy tests. Fetched remote main and confirmed the previous multiple-contact PR was squash-merged as `7405a36`; created `feat/checkout-observability` from `origin/main`.

Implemented a simulated AI assistant checkout surface on the participant page. The protected-action endpoint, challenge issuance, reviewer decision and completion path remain the same backend flow; this is not a shopping agent, merchant integration or real payment network. The page states the checkout is simulated and no real payment occurs.

Added optional Sentry observability hooks in `callgate/sentry_observability.py`, wired into broker transcript ingestion, challenge creation, reviewer decisions and direct gateway refusal. The hooks are disabled unless `CALLGATE_SENTRY_DSN` is present or tests pass a fake transport. The sanitizer keeps session hashes, state names, event types, durations, outcome statuses and error codes, and drops transcript text, destinations, plain amounts, contact identity fields and challenge responses. `send_default_pii` is disabled when the optional Sentry SDK is configured. Added an `observability` optional dependency entry.

Test-first evidence: `tests/test_telemetry_privacy.py` captures emitted records with a fake transport and verifies a sensitive transcript, amount, destination and contact-like fields do not appear. Initial expected session hash was wrong and was corrected after the failing assertion showed the actual hash. The managed sandbox currently hangs on FastAPI `TestClient` local ASGI calls, including a minimal app, so TestClient-based checks were run with normal execution permissions.

Actual final checks:
- `python -m pytest tests/test_telemetry_privacy.py -q -p no:cacheprovider`: 2 passed, 2 deprecation warnings.
- `python -m pytest -q -p no:cacheprovider`: 242 passed / 245 collected, 3 optional integration skips, 2 deprecation warnings.
- `node --test tests/review_ui.test.cjs`: 1 passed / 1 test; `node --check callgate/demo/review-ui.js` passed.
- `python scripts/check_claims.py`: registered=31, unresolved_or_inconsistent=0.
- `python evaluation_v2/verify_inputs.py`: 90 scripts / 30 correlated families, manifests/schema verified, no CallGate predictions run.
- Actual launcher smoke with automatic loopback ports: fetched participant page and verified the checkout-skin text. The first smoke attempt inside the managed sandbox failed with `PermissionError: [Errno 1] Operation not permitted` when creating a socket; reran with normal execution permissions and stopped all spawned processes.
- `git diff --check`: passed.

Remaining for this increment: PR publication. No real Sentry project trace/screenshot, Session Replay, or observability-driven performance fix has been recorded yet; do not claim one until it exists.

## 2026-10-08 — Checkout safety-utility rehearsal

Owner requested continued development. Fetched remote main and confirmed the checkout-observability PR was squash-merged as `18f0cf1`; created `feat/commerce-utility-eval` from that main snapshot. Read PROJECT_TRUTH, FEATURE_LEDGER, latest BUILD_LOG and git history.

Implemented `evaluation_checkout`, a small synthetic checkout rehearsal for the sponsor-facing commerce story. It compares three systems: deny-all, unguarded checkout, and CallGate's existing simulated approval path. The output keeps raw numerators/denominators for false execution and legitimate completion, Wilson intervals for descriptive proportions, and synthetic reviewer-response timing. It writes machine-readable JSON plus a short Markdown report. It does not use frozen v1 holdout labels, run evaluation_v2 predictions, touch real payments, or claim independent annotation.

Initial run exposed a useful scenario-design issue: only 1 of 3 legitimate checkout cases completed because two natural checkout phrasings did not trigger the current high-impact payment rule. The legitimate rehearsal cases were narrowed to explicit high-impact payment requests so the utility slice measures the existing reviewer-approved payment path instead of ordinary shopping conversation.

Actual final checks:
- `python -m evaluation_checkout.run`: scenario_count=6; systems deny_all, unguarded_checkout, callgate; CallGate false_execute 0/3 and legitimate_completion 3/3 in this synthetic rehearsal; deny_all legitimate_completion 0/3; unguarded false_execute 3/3.
- `python -m pytest tests/test_checkout_evaluation.py -q -p no:cacheprovider`: 3 passed.
- `python -m pytest -q -p no:cacheprovider`: 245 passed / 248 collected, 3 optional integration skips, 2 deprecation warnings.
- `node --test tests/review_ui.test.cjs`: 1 passed / 1 test; `node --check callgate/demo/review-ui.js` passed.
- `python scripts/check_claims.py`: registered=31, unresolved_or_inconsistent=0.
- `python evaluation_v2/verify_inputs.py`: 90 scripts / 30 correlated families, manifests/schema verified, no CallGate predictions run.
- `git diff --check`: passed.

Remaining for this increment: PR publication. The rehearsal is synthetic and author-written; do not claim real shopping conversion or measured human response time.

## 2026-10-08 — Generated checkout safety-utility figure

Owner requested continued development. Fetched remote main and confirmed the checkout safety-utility rehearsal PR was squash-merged as `e176bd0`; created `feat/checkout-safety-utility-figure` from that main snapshot.

Implemented a generated SVG figure for the checkout rehearsal. `python -m evaluation_checkout.run` now writes `evaluation_checkout/safety_utility.svg` in addition to the JSON and Markdown report. The figure plots legitimate checkout completion on the x-axis and false execution on the y-axis using the generated raw counts, not hand-entered slide numbers. The README and commerce rehearsal docs now point to the generated figure. This is a presentation artifact, not a new measurement or real commerce telemetry.

Actual final checks:
- `python -m evaluation_checkout.run`: regenerated JSON, Markdown and SVG; CallGate false_execute 0/3 and legitimate_completion 3/3 in this synthetic rehearsal.
- `python -m pytest tests/test_checkout_evaluation.py -q -p no:cacheprovider`: 4 passed.
- `python -m pytest -q -p no:cacheprovider`: 246 passed / 249 collected, 3 optional integration skips, 2 deprecation warnings.
- `node --test tests/review_ui.test.cjs`: 1 passed / 1 test; `node --check callgate/demo/review-ui.js` passed.
- `python scripts/check_claims.py`: registered=31, unresolved_or_inconsistent=0.
- `python evaluation_v2/verify_inputs.py`: 90 scripts / 30 correlated families, manifests/schema verified, no CallGate predictions run.
- `git diff --check`: passed.

Remaining for this increment: PR publication. The SVG is generated from synthetic rehearsal counts and must not be presented as a new measurement.

## 2026-10-09 — OTP coercion baseline and honest checkout utility loss

Owner pointed out seven claim risks before the next PR: safety monotonicity must have randomized property tests before README claims it; contact challenge tests need counted evidence; Sentry privacy tests must capture all outbound telemetry; local multi-contact keys do not prove independent humans; checkout utility was too clean without contact availability and delay; deny-all/unguarded were weak baselines without OTP step-up; and the figure must not hide that risk blocking is scripted.

Fetched remote main and confirmed the generated-figure increment was squash-merged as `1fd99dd`. Continued on `feat/otp-coercion-checkout-eval`.

Implemented an OTP step-up baseline and CallGate contact-availability/latency variants in `evaluation_checkout/run.py`. The OTP baseline completes every checkout, but unauthorized pressure scenarios are counted as false execution because the scripted victim relays the OTP to the attacker. CallGate is now reported as `callgate_p100_fast`, `callgate_p67_observed`, and `callgate_p67_slow`; the two p=0.67 variants model one unavailable legitimate contact, and the slow variant multiplies response latency. Regenerated `evaluation_checkout/results.json`, `evaluation_checkout/REPORT.md`, and `evaluation_checkout/safety_utility.svg`.

Updated docs to keep the claim honest: README now names the OTP coercion baseline and contact availability/delay parameters; the role-separation boundary explicitly says the multi-contact launcher still runs on one host under one operator's control, so one person controlling all processes can self-approve. `docs/COMMERCE_IMPACT_REHEARSAL.md` and `docs/PROJECT_TRUTH.md` now state that these are author-written scripted assumptions, not real human response or commerce telemetry.

Audit evidence requested by owner:
- Safety monotonicity property test exists in `tests/test_safety_properties.py::test_revisions_duplicates_and_order_do_not_relax_safety`. Actual run: `python -m pytest tests/test_safety_properties.py --hypothesis-show-statistics -q -p no:cacheprovider` -> 1 passed; Hypothesis generated 1000 passing, 0 failing, and 83 invalid test cases. It checks random transcript sequences plus repeated/older revisions do not move to a less restrictive state and never allow protected actions.
- Contact binding / cross-contact / replay / tamper evidence: `python -m pytest tests/test_contact_binding.py tests/test_multiple_contacts.py tests/test_review_process.py --collect-only -q` collected 35 tests. The collected cases include wrong saved-contact key rejection, same credential origin self-approval rejection, five parameter-scope tamper cases, denied/expired challenge survival across identity and amount changes, duplicate identity rejection, shared key rejection, old decision rejection after amount change, wrong reviewer/addressee rejection, broker route isolation, seven ambiguous/overlapping capability-token startup rejections, superseded identity hiding and old signature invalidation, participant/unknown capability rejection, and two-/three-process routing isolation.
- Privacy telemetry evidence: `tests/test_telemetry_privacy.py` passes a fake `telemetry_transport=captured.append` into the broker app, captures all emitted records, serializes the entire captured payload, and asserts the known sensitive transcript string `Send 9876543 dollars`, `secret phrase`, amount `9876543`, destination `alice-private-wallet`, contact-like `Alice`, and reviewer token text do not appear. It also checks only sanitized evidence such as `session_hash`, `CHALLENGED`, and `POLICY_PROOF_REQUIRED` remains.

Actual checkout results from `python -m evaluation_checkout.run`: scenario_count=6; `deny_all` false_execute 0/3 and legitimate_completion 0/3; `unguarded_checkout` false_execute 3/3 and legitimate_completion 3/3; `otp_step_up` false_execute 3/3 and legitimate_completion 3/3; `callgate_p100_fast` false_execute 0/3 and legitimate_completion 3/3 with median 24000 ms and p95 30000 ms; `callgate_p67_observed` false_execute 0/3 and legitimate_completion 2/3 with median 21000 ms and p95 24000 ms; `callgate_p67_slow` false_execute 0/3 and legitimate_completion 2/3 with median 84000 ms and p95 96000 ms.

Actual final checks:
- `python -m evaluation_checkout.run`: regenerated JSON, Markdown and SVG with OTP and contact-availability variants.
- `python -m pytest tests/test_checkout_evaluation.py -q -p no:cacheprovider`: 4 passed.
- `python -m pytest tests/test_safety_properties.py --hypothesis-show-statistics -q -p no:cacheprovider`: 1 passed; 1000 passing, 0 failing, 83 invalid Hypothesis cases.
- `python -m pytest tests/test_contact_binding.py tests/test_multiple_contacts.py tests/test_review_process.py -q -p no:cacheprovider`: 35 passed, 2 warnings.
- `python -m pytest tests/test_telemetry_privacy.py -q -p no:cacheprovider`: 2 passed, 2 warnings.
- `python -m pytest -q -p no:cacheprovider`: 246 passed / 249 collected, 3 optional integration skips, 2 warnings.
- `node --test tests/review_ui.test.cjs`: 1 passed / 1 test.
- `node --check callgate/demo/review-ui.js`: passed.
- `python scripts/check_claims.py`: registered=31, unresolved_or_inconsistent=0.
- `python evaluation_v2/verify_inputs.py`: 90 scripts / 30 correlated families, manifests/schema verified, no CallGate predictions run; all slices are small and should not report F1 as validated evidence.
- `git diff --check`: passed.

Remaining for this increment: PR publication. No real Sentry project trace/screenshot, Session Replay, observability-driven performance fix, real human response data, or real commerce telemetry has been recorded yet.

### 2026-10-17 — UCLA onsite device inbox

Operator reports existing text, AssemblyAI and saved-contact demos already working locally. Added a separate loopback device intent receiver + authenticated inbox view, persistent idempotency and device-scoped credentials. Kept existing participant/reviewer services separate. Prepared iPhone HTTP contract and opt-in HTTPS tunnel instructions; no public endpoint started, secrets inspected, deployment, push or merge performed. See `docs/DEVICE_EVENTS.md` and `FEATURE_LEDGER.md` for scope and boundaries.

Validation for this increment: isolated inbox 10 tests passed. Regression run excluding `tests/test_safety_properties.py`: 255 passed, 3 skipped; Node review UI test passed; `git diff --check` passed. Full Python collection was blocked by missing `hypothesis` in the existing virtual environment; dependencies were not changed. TestClient required execution outside the sandbox. No live iPhone or HTTPS tunnel test was performed.

### 2026-10-17 — authorized temporary tunnel attempt and missing property tests

User authorized exposing only device inbox. Started loopback 127.0.0.1:8780 with freshly generated local-only dedicated credentials under ignored mode-700 `.test-tmp/device-live/`. Installed official cloudflared 2026.10.1 locally; started temporary HTTP/2 tunnel with explicit empty config and only origin 8780. URL allocated, but edge connection failed: TCP/UDP 7844 startup checks fail and public POST returns HTTP 530. Public auth/binding/idempotency validation remains incomplete; local real HTTP checks all passed. Processes retained for network change/retry; scoped stop tool provided. No participant/reviewer exposure, push or merge.

Installed exact `requirements-safety.txt` dependencies via uv: hypothesis 6.168.5, sortedcontainers 2.4.0. Property test (1000 examples) passed; focused 11 passed; full Python run 256 passed, 3 skipped, 2 deprecation warnings. This supersedes the previous missing-Hypothesis limitation. Hardware/iPhone end-to-end remains unverified.

### 2026-10-17 — ngrok fallback preparation

Per explicit user instruction, stopped only cloudflared PID 3341 after matching its command line; retained inbox PID 2797, credentials and database. Campus network retained. Installed ngrok 3.39.11 from official Linux standalone download; credential-free bounded diagnostics passed DNS/TCP/TLS/tunnel protocol in us-cal-1. No account config exists; user instructed to configure authtoken locally using hidden-input helper. No token read/printed by assistant, no usable ngrok endpoint or public application checks claimed yet. Prepared bounded-start device-only launcher and smoke checks with independent UUIDs and cleanup limited to this test invocation. No persistent network retries, push or merge.

### 2026-10-17 — ngrok public contract verified

After operator configured authtoken locally, launched ngrok and checked actual upstream exactly http://127.0.0.1:8780. HTTPS endpoint https://device.example.invalid is live. Public checks passed: unauthenticated GET/POST 401, verify/help accepted 201, duplicate 200 preserving event, wrong device_id 403, conflicting ID 409, device cannot read 401, viewer read 200, participant/reviewer/openapi/.env 404. Independent ngrok-check UUIDs cleaned up; original credentials, database and prior records retained. Service and tunnel left running. No authtoken or device/viewer credentials printed; no push/merge. Actual iPhone/BLE button remains for teammate acceptance.

### 2026-10-17 — dashboard route recheck after Windows localhost 404

Verified live PID 2797 command/cwd and ngrok upstream. Existing GET / dashboard returned HTTP 200 text/html with expected title from both WSL localhost and public ngrok HTTPS. Viewer event GET 200 and device event GET 401 on both origins. No restart or data/credential changes. Windows-browser localhost 404 source remains undetermined; direct user to verified HTTPS root dashboard, enter raw viewer.token in the page's password field. Prior Windows localhost reachability assumption is corrected; no claim of Windows loopback forwarding verification.

### 2026-10-17 — isolated local wearable/workflow fusion

Preserved live inbox PID 2797 and ngrok origin/address/credentials/database without restart. Added optional local adapter to original broker and policy workflow; read-only inbox access, explicit actual-session/device/saved-contact/operation binding, persistent event claim before original challenge creation, no pending replacement, original signed reviewer path, and actual-state-only timeline. New local instance on 127.0.0.1:8781 (/fusion), separate reviewer 8782, credentials in ignored `.test-tmp/fusion-live/`; default demos unchanged. No migration of an old separate session; operator starts fresh consented evidence and binds this instance.

Live checks: fusion HTML/JS 200; operator snapshot 200, no credential 401, initially unbound. Original inbox page 200; ngrok still https://device.example.invalid → 127.0.0.1:8780; public /fusion, /api/fusion, /api/review/pending all 404. No test events inserted into current phone inbox, no binding/consent/request automatically performed. Full instructions and explicit limits: docs/DEVICE_FUSION.md. Real teammate BLE/iPhone→local operator→contact response remains unverified. No restart of live services, push or merge.

Final validation for local fusion increment: focused Python integration 15 passed; full Python 271 passed / 3 skipped with 2 existing TestClient deprecation warnings; Node UI 6 passed; diff whitespace checks passed. New local instance left unbound pending explicit operator consent/evidence/binding. No phone inbox test data added.

### 2026-10-17 — fresh manual intent and visible challenge label

At operator request, preserved current bound CHALLENGED session (pending=false) and sent exactly one new local verify_request via 8780 with event_id prefix `local-manual-test-20261017T234509Z-`. Inbox returned 201; fusion reports intent_received and no creation refusal. Did not create a confirmation or reset session. Original credentials, DB, ngrok and processes retained. Frontend previously included challenge in JSON; added an explicit bold local-only challenge label for currently pending request_created records, hidden for invalidated records. Four focused Node UI tests pass using synthetic challenge fixture; no live challenge or credential printed. Actual script/page served from live local app checked without restart.

### 2026-10-17 — reviewer request visibility diagnosis

Observed former manual request no_longer_pending while expires_at was still ~39s in future; context CHALLENGED, pending=false, authorization_denied=false, outcome=null. Cannot attribute this observed disappearance to expiry; original accepted-transcript invalidation reproduces this state, but historical invalidating action is not audited and remains undetermined. Saved reviewer link points to current fusion 8782, authenticated API 200/null, no credential 401. No evidence of wrong saved backend or API failure mapped to null.

Static UI changes without restart: reviewer displays own origin, request ID and contact route; distinguishes credential/network errors from successful empty response; allows replacing cached role credential using same-origin local full reviewer entry in password field. Fusion instructions warn that new transcript invalidates pending. Thirteen Node UI tests pass; added explicit integration regression for pre-expiry transcript invalidation. No credential/challenge printed, no live process reset, no push/merge.

Live follow-up verified: created explicit local-manual-reviewer-check-12668579-8638-4e7c-b683-b31f833964c0 request using current binding, with same session retained. Fusion, broker reviewer route and 8782 reviewer API all returned the same request_id (prefix cd9e8d824798); pending=true, 119 seconds remained at verification. Did not approve or print challenge. Reviewer HTML/JS both 200. Focused Python integration/process tests 18 passed. Match report kept locally in .test-tmp/fusion-live/reviewer-match-check.json. Original live services retained.

### 2026-10-17 PDT — operator-completed local manual verification

Read-only reconciliation confirmed actual completed event `-983168`, request `20636a1139e81f8e31032a9b63ff3ea9966e5cacc02db2248880a84250640883`, matches current workflow outcome. Actual UTC timeline: received 23:52:38.275077; request created 23:57:15.080850; signed approval accepted 23:58:15.011402; simulated result 23:58:15.011423. Result simulated_action_completed, real_action_executed=false, saved-family, fictional-wallet, 100 USD cents. Classified per operator as LOCAL_MANUAL_TEST, excluded from phone/BLE/hardware validation. Earlier local-manual-reviewer-check request did not complete and is not combined with these timestamps. Full record: docs/LOCAL_MANUAL_VERIFICATION_2026-10-17.md. No service or tunnel restarted/stopped; original ngrok origin still 127.0.0.1:8780 and inbox page 200. No secrets printed, no database edits, no push/merge.

### 2026-10-17 PDT — ReachGuard English presentation and UX

Reworked opt-in local fusion operator, participant and reviewer static assets into ReachGuard: “Reach someone you trust. Before you act.” Added navy/warm-white/teal responsive hierarchy, evidence provenance, explicit simulated-action card, fixed event selection, factual timeline, progressive setup/developer details, clear challenge countdown, stale/expired/disconnected-code suppression, distinct contact states, keyboard focus and reduced-motion support. All surfaced product copy is English; protected legacy 8780 diagnostic page left unchanged. Default illustrative text/amount apply only to new input forms; existing session/binding not mutated.

Added local CLI role opener using private existing role files, not a web endpoint: operator uses participant authority, reviewer retains separate capability. No new policy, enrollment, identity, payment, delivery or hardware assurance is claimed. Original protocols and expiry remain authoritative. No new telemetry destinations. No process restart or live event writes during this UI increment; 8780 PID 2797, fusion/reviewer PIDs 5272/5271 and existing ngrok upstream 127.0.0.1:8780 retained.

Validation: full Python 277 passed / 3 skipped (2 existing TestClient warnings), Node UI 21 passed. Optional browser tooling isolated in .test-tmp; required libraries locally extracted after sudo install was unavailable, without system installation. Actual Chromium desktop/mobile acceptance: 11 scenario groups, 10 screenshots, zero page errors, synthetic local fixtures only with all APIs intercepted. Visually inspected waiting/success/denial/expiry and corrected expired badge/disabled controls. Separate real-role browser read-only checks passed, zero mutation requests, no screenshots of real data. Original public root 200, unauthenticated device read 401; public fusion/reviewer routes remain 404. Desktop OS launcher, real Safari/iPhone/BLE and human comprehension/accessibility audit remain unverified. Details: docs/REACHGUARD_UI.md. No credentials/challenges printed, no push/merge/deployment.

### 2026-10-17 PDT — independent Reach help and local publication handoff

Implemented independent help response store/transport, contact and Dashboard pages, separate owner/contact/dashboard permissions, persistent event import/audit, idempotent actions, terminal cancellation and serialized concurrent responses. It reads the original device inbox without modifying its data or API; no payment workflow/policy/challenge is required. Existing payment demo remains local. New runtime provisioning uses random actor identities and preserves existing credentials.

Validation: final full Python suite 292 passed, 3 skipped, 2 existing dependency deprecation warnings; independent help backend tests 15 included. JavaScript 24 tests passed across four files. Synthetic provisioning check verified independent identities and credential retention. Initial sandboxed suite stalled on restricted localhost access; only that pytest was stopped, and the full suite passed with localhost access. Read-only live HTTP checks: inbox, fusion, reviewer, help Dashboard/contact all HTML 200; three help roles returned scoped status 200. Original ngrok still has one endpoint forwarding only to 127.0.0.1:8780. No live help acceptance/cancellation was performed. Earlier payment UI browser checks are recorded separately; independent help mobile visual/interaction testing remains pending.

Separate help HTTPS startup failed with ERR_NGROK_313; only its new agent stopped, original device tunnel retained. Arduino BLE and custom Swift gateway remain unverified. Operator reports Shortcut HTTPS upload completed; local manual payment verification does not count as hardware testing. Handoff: docs/REACH_INTEGRATION_HANDOFF.md. Historical live public domains replaced with placeholders in publishable documentation/tests; runtime files untouched. Known private role values and credential patterns checked without printing values; no runtime databases, private links/configuration or screenshots staged. User requested local commit only; no push or merge attempted.

### Reach phone help HTTPS — follow-up after merged integration

Fetched origin and confirmed the merged integration tree; started new branch feat/reach-phone-help from origin/main without reset or worktree loss. Diagnosed the previous ERR_NGROK_313 from redacted existing logs: Free-plan custom-subdomain binding denied. Official free-plan limits confirm only the assigned development domain is available. Removed the launcher's invented custom-domain fallback; --url is now required and a regression test verifies missing configuration fails before network/account operations.

Preserved the original device ngrok origin, upstream 127.0.0.1:8780, credentials and database, without restarting any service. Made one separate localhost.run SSH connection forwarding only 127.0.0.1:8783, with its own known-hosts file, no private SSH identity/agent, bounded startup and keepalives, no restart loop. Actual forwarding origin was extracted from the accepted forwarding event, excluding the provider administration URL, then verified using HTTPS. Runtime origin/PID/logs stay ignored and are not checked into source. No payment routes exposed.

Real HTTPS local automated test: a unique local-test-help-https event uploaded through unchanged device HTTPS returned 201, repeat 200, wrong-device attempt 403. Help status without auth/device auth 401; owner cannot respond as contact and contact cannot cancel (403). Actual Chromium 390x844 public contact page selected only that local test and clicked I can help; same event became Contact accepted in the local read-only Dashboard. One applied acceptance retained after identical response retry. No API interception, screenshots or credential disclosure; zero page errors/overflow. This is LOCAL_AUTOMATED_HTTPS_TEST_NOT_PHONE_OR_BLE, not actual iPhone/hardware evidence. Private evidence retained under .test-tmp/help-live/public-check.json.

Final validation: Python 293 passed / 3 skipped / 2 existing deprecation warnings; all four Node frontend test files pass (24 individual tests); claims guard registered=33 unresolved_or_inconsistent=0; diff whitespace check clean. Final local/public device and public help contact/Dashboard pages all 200, original ngrok endpoint unchanged. Real iPhone response and Arduino BLE/Swift remain pending. Updated docs/REACH_PHONE_HELP.md and integration handoff. No push or merge performed; follow-up changes remain on the new branch.

### Reach help endpoint rotation recovery

Operator reported the old contact origin showed No tunnel. Read-only diagnostics found the original localhost.run SSH process still alive and the local 8783 contact page returning the expected HTML 200. Its log contained a second accepted forwarding registration with a different public origin. The old origin no longer served the app (HTTP 502 on verification); the latest origin served the correct contact HTML 200. This is consistent with the provider's documented temporary free-domain rotation, rather than a stopped local help service. No process restart or replacement tunnel was needed.

Updated only the ignored help-base-url.txt to the latest verified origin and saved redacted check outcomes in ignored endpoint-recovery.json. Public help API: missing, invalid and device credentials each 401; existing contact credential 200 with contact role. No response/cancellation actions were sent and no role credentials or databases were changed. Device 8780 remained HTML 200; original ngrok agent still had its single endpoint targeting 127.0.0.1:8780. The phone must use the new contact URL with the same separate contact code. No stable-domain claim is made. No push or merge.

### Frozen demo — actual operator-confirmed iPhone help response

Read-only database reconciliation uniquely matched event 65b46c58-0b40-4793-8a47-5eb9b695cd1b, device nano-01, help_request. Inbox receipt 2026-10-18T02:45:10.007152+00:00; independent help record 02:45:10.900874; applied assigned-contact acceptance 02:49:45.781187. Exactly two audit entries, one applied acceptance, current accepted version 1, no unable/cancel/rejected action for this event. Dashboard Contact accepted is operator-reported; no persisted display timestamp exists. User attributes trigger to phone Shortcut and response to real iPhone; server independently confirms receipt and contact-role action, not device hardware/client provenance. Classified PHONE_SHORTCUT_TRIGGER_AND_IPHONE_CONTACT_RESPONSE, excluded from Arduino/BLE/Swift validation and separate from prior automated/local-manual test events.

Added observed evidence and detailed recovery recipes for 8780, original ngrok, help 8783 and separate SSH tunnel, without executing recovery against healthy services. Initial provisioning start_local.py is explicitly not a restart tool; instructions reload existing secrets/DB instead. Documented free-domain rotation and verified-origin lookup, independent role handoff, remaining real-phone failure-path checks and hardware gaps. No features added; functionality frozen. Credentials, private configuration, runtime evidence JSON, logs and databases remain ignored. Local commit requested, no push or merge.

Freeze validation: focused help/inbox/launcher/claims regression 31 passed (2 existing dependency warnings); full suite on the same code snapshot previously 293 passed / 3 skipped. Claims guard registered=33 unresolved_or_inconsistent=0. Both documented Python recovery recipes compile without execution; restart steps deliberately not tested on healthy live processes. Source/tracked-file sensitive scan covered 218 files, zero findings. Final public contact HTML 200 and scoped contact status matched the accepted phone event with two history entries; original device origin still forwards only to 8780. No credentials printed or runtime artifacts selected for commit.
