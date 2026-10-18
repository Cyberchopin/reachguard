# LA Hacks feature attribution

Source baseline: `e72e85a22a6ec0ef19f0a9ee07b4093eb8af7753`.
The baseline commit contains the following existing capabilities; it is a containment reference, not a claim that each feature originated in that commit.

| Capability | Attribution | Source | Containing commit |
|---|---|---|---|
| Live AssemblyAI and text fallback | PRE_EXISTING | `callgate/review_transport.py`, `scripts/start_review_demo.py` | `e72e85a` |
| English rules and four-state policy | PRE_EXISTING | `callgate/engine.py` | `e72e85a` |
| Revision-aware evidence graph and receipts | PRE_EXISTING | `callgate/evidence_graph.py`, `callgate/receipt.py` | `e72e85a` |
| Separate-role scoped simulated approval | PRE_EXISTING | `callgate/confirmation.py`, `callgate/workflow.py` | `e72e85a` |
| Bounded numeric SQLite measurements | PRE_EXISTING | `callgate/live_metrics.py` | `e72e85a` |
| Author-labeled pilot and frozen first run | PRE_EXISTING | `evaluation_v1/` | `42f0af8`, contained in `e72e85a` |
| P0–P5 documentation/data/check tools | PRE_EXISTING once merged | This patch; no product feature implementation | Pending user PR commit |

## Event additions — leave empty until actually built

User-directed final-product implementation began before the future event. The local increment below must not be attributed to that future event. After the user's PR, record its real commit SHA.

| New local capability | Actual attribution | Evidence |
|---|---|---|
| Bounded bilingual text extraction and monotone policy | BUILT_NOW, pending user PR | `callgate/safety_policy.py`, property/fixture tests |
| Session authorization-denial latch | BUILT_NOW, pending user PR | `callgate/workflow.py`, denial/expiry tests |
| Direct protected-action rejection and visible UI test | BUILT_NOW, pending user PR | `callgate/review_transport.py`, `participant.html` |
| Counterfactual-plus-valid-approval rehearsal | BUILT_NOW, pending user PR | `scripts/proof_demo.py` |
| Truth/claims/input validation and documentation | BUILT_NOW, pending user PR | `CLAIMS.md`, `evaluation_v2/`, `docs/` |

| Intended addition | Attribution | Start/finish commit | Evidence |
|---|---|---|---|
| Evidence monotonicity with revision semantics | | | |
| Mandarin / code-switch evidence extraction | | | |
| Enrolled, claimed-identity-bound contact challenge | | | |
| Self-approval rejection and independently scoped gateway | | | |
| Detector-failure replay over controlled simulator | | | |
| Joint authorization safety and legitimate-request utility evaluation | | | |

## Rules audit

Saved-contact increment merged as `6855522`. Current follow-up: multiple synthetic saved contacts with distinct reviewer processes and bearer routes, BUILT_NOW; source `scripts/start_review_demo.py`, `callgate/review_transport.py`, tests in `test_multiple_contacts.py` and `test_review_process.py`. Remote device delivery and verified human enrollment remain incomplete.

Multiple-contact increment merged as `7405a36`. Current follow-up adds a simulated AI checkout surface over the same protected-action and reviewer flow plus optional Sentry-style trace/log hooks with privacy filtering, BUILT_NOW. Source `participant.html`, `callgate/sentry_observability.py`, `callgate/review_transport.py`, and `tests/test_telemetry_privacy.py`. No payment network, merchant, DSN, external Sentry project, Session Replay, or production observability is included.

Checkout-observability increment merged as `18f0cf1`. Current follow-up adds a controlled checkout safety-utility rehearsal comparing deny-all, unguarded checkout and CallGate's existing simulated approval path; BUILT_NOW. Source `evaluation_checkout/run.py`, generated `evaluation_checkout/results.json` and `evaluation_checkout/REPORT.md`, docs in `COMMERCE_IMPACT_REHEARSAL.md`, and tests in `tests/test_checkout_evaluation.py`. This is synthetic author-written evidence, not independent labels or real commerce telemetry.

Commerce rehearsal increment merged as `e176bd0`. Current follow-up adds the generated safety-utility SVG figure from the same checkout rehearsal JSON; BUILT_NOW. Source `evaluation_checkout/run.py`, `evaluation_checkout/safety_utility.svg`, and tests in `tests/test_checkout_evaluation.py`. This is a generated presentation artifact, not a new measurement.

Generated-figure increment merged as `1fd99dd`. Current follow-up adds an OTP step-up coercion baseline plus CallGate contact availability/latency variants to the checkout rehearsal; BUILT_NOW. Source `evaluation_checkout/run.py`, generated report/JSON/SVG and tests in `tests/test_checkout_evaluation.py`. These are scripted parameters, not observed user behavior.

Owner squash-merged the previously pending local increment as `1882e3d` on 2026-10-06. The pending labels above describe the original audit snapshot. Current follow-up adds trusted-startup saved-contact routing and credential-origin checks (`callgate/contacts.py`, `tests/test_contact_binding.py`); BUILT_NOW, not future-event work. Independent human enrollment and remote delivery remain incomplete.

Official URL: https://la-ai-hackathon-2026.devpost.com/rules
Accessed 2026-10-05. Pre-existing open source is allowed; only clearly disclosed new event features are judged. The page also contains an April deadline inconsistent with the October event header. Confirm final timing with organizers; do not invent an exact coding duration.

## UCLA onsite increment — 2026-10-17

Per operator's onsite context, existing text/AssemblyAI demos, saved-contact verification and scoped simulated approval predate this increment. New: isolated device intent inbox (`callgate/device_events.py`), loopback launcher on 8780, device-bound Bearer authentication, separate read-only dashboard credential, persistent SQLite event-id deduplication, two intent types, focused tests, and HTTPS tunnel preparation (`docs/DEVICE_EVENTS.md`). No BLE/iPhone implementation, automatic contact delivery, payment authority, public tunnel, deployment or merge is claimed. Exact event eligibility is not independently verified here.

2026-10-17 onsite follow-up: user-authorized device-only temporary tunnel attempted; local inbox running and local real HTTP contract verified. Public edge unreachable on outbound TCP/UDP 7844 (HTTP 530), so remote delivery and actual iPhone/BLE event are not claimed. Exact safety-test dependencies installed; previously omitted property test now passes, full Python 256 passed / 3 skipped. Runtime credentials and processes remain local-only; no existing participant/reviewer service published.

2026-10-17 follow-up: ngrok device-only HTTPS entry now running; public authentication, device binding, persistent deduplication and route isolation verified over real HTTPS. Independent test events cleaned; original inbox retained. This establishes backend public delivery readiness, not actual BLE/iPhone button completion, contact verification completion or payment authorization.

## UCLA onsite local workflow fusion — 2026-10-17

PRE_EXISTING: bilingual monotone policy, processing consent, saved-contact routing, six-digit challenge, independent reviewer signing process, denial latch and scoped simulated execution (`workflow.py`, `confirmation.py`, `review_transport.py`).

NEW_ONSITE: opt-in local fusion operator page and read-only device inbox adapter; explicit binding to this local instance's actual session/device/contact/simulated operation; persistent per-event claims before challenge issuance; policy/session/pending/audio guards; factual event→request→accepted signed response→simulation timeline; separate loopback fusion broker/reviewer on 8781/8782; private role files; integration/UI tests. Sources: `callgate/device_fusion.py`, `callgate/demo/device-fusion.*`, opt-in launcher flags, `tests/test_device_fusion.py`, `tests/device_fusion_ui.test.cjs`.

NOT_CLAIMED: migration of an already-running separate participant session, automatic processing of past events, hardware/iPhone-to-contact human acceptance, real contact enrollment or notification, production crash recovery, payment authority. Existing 8780/ngrok process, origin, credentials and data retained. See `docs/DEVICE_FUSION.md`.

Observed local manual completion (2026-10-17 PDT): operator-approved request `20636a1139e8…` / event `-983168` has all four persisted stages and matching simulated_action_completed workflow outcome, real_action_executed=false. Count only as LOCAL_MANUAL_TEST, expressly excluded from phone/hardware validation. See `docs/LOCAL_MANUAL_VERIFICATION_2026-10-17.md` for exact times and remaining limits.

## ReachGuard English UI/UX — 2026-10-17 onsite presentation increment

PRE_EXISTING: all device receive/auth/idempotency semantics, CallGate policy/consent, contact directory, original challenge/signature/expiry/replay protection, local fusion binding/claims and factual timeline.

NEW_UI_ONLY: ReachGuard English operator/request/reviewer surfaces; responsive navy/white/teal design; progressive configuration, readable evidence and simulated-action summaries, stable event selection, original-expiry countdown and obsolete-code hiding, distinguishable error/denial/expiry/completion states, correct current role links, local CLI opener retaining separate role files, UI unit/browser checks and labeled synthetic screenshots. No new security or hardware-validation capability. 8780/ngrok/API/credentials/data preserved without restart. See docs/REACHGUARD_UI.md for evidence and remaining limits.

## Reach independent help response — onsite follow-up

PRE_EXISTING: device inbox authentication, durable deduplication, read-only event storage and the separate CallGate payment demo.

NEW: independent help store and audit, scoped contact accept/unable responses, owner cancellation, read-only Dashboard/status, serialized concurrent actions and separate local role files. These do not require payment policy, amounts or challenge codes. Backend and JavaScript tests use isolated synthetic data. Local service runs on 8783; separate help HTTPS attempt failed with ERR_NGROK_313 and was stopped without changing the original device tunnel. Arduino BLE, Swift gateway, mobile help UI and public help response closure remain unverified. See docs/REACH_INTEGRATION_HANDOFF.md.

## Frozen phone demonstration — observed 2026-10-17 PDT

PRE_EXISTING for this follow-up: independent help state machine, role boundaries, audit and Dashboard; no new security or UI capability added. NEW EVIDENCE: operator-confirmed phone Shortcut trigger and real iPhone contact acceptance, matched by full event_id against the retained device inbox and assigned-contact audit. Event ends b695cd1b; actual receipt, help record and acceptance times are documented in docs/IPHONE_HELP_VERIFICATION_2026-10-17.md. This is phone evidence, expressly not Arduino/BLE/Swift verification. Added recovery handoff and frozen-demo validation gaps in docs/REACH_DEMO_RECOVERY.md. No service restart for handoff, no real emergency dispatch or help-arrival claim.
