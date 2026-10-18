# CallGate verified project truth

Audit date: 2026-10-05 (America/Los_Angeles). Source snapshot:
`e72e85a22a6ec0ef19f0a9ee07b4093eb8af7753`.

Authority order: executable code and observed commands, archived immutable results, then documentation. No claim of a remotely passing CI or real-world safety follows from this file.

## Seed facts

| Seed | Status | Evidence and qualification |
|---|---|---|
| Four Conversation states exist; VERIFIED_BOUNDED and ESCALATED do not | VERIFIED | `callgate/engine.py: Conversation.ingest/snapshot`; `callgate/receipt.py` closed literal. These are risk states, not verified identity. |
| Launcher is `python -m scripts.start_review_demo` | VERIFIED (source) | `scripts/start_review_demo.py` executable entry and argparse; not a live two-device/browser test in this audit. |
| Saved report reproduction is `python -m evaluation_v1.evaluate_pilot render` | VERIFIED (execution) | Executed locally, exit zero, archived CallGate confusion TP=1 FP=0 FN=7 TN=8. No fresh inference or API calls. |
| Pilot contains development and holdout calls | VERIFIED (archive scope) | `evaluation_v1/manifest.json`: development input/label rows 36; initial test input/label rows 24. Private originals are absent from this clone; raw archive includes revealed cases. |
| Holdout is revealed | VERIFIED | `evaluation_v1/pilot_results/raw.json` status `UNVALIDATED_SYNTHETIC_PILOT_TEST_NOW_REVEALED`; do not tune on it. |
| First CallGate recall is 1/8; baseline 2/8 | VERIFIED | `results.json` and executed renderer. CallGate TP=1 FN=7; baseline TP=2 FN=6. |
| Local historical check says Python tests passed | VERIFIED as historical record ONLY | `scambench/local-check.json`: tests=184, failures=0, errors=0, skipped=0. This is not the current audit run. |
| This audit reproduces all historical Python passes | CONTRADICTED in current environment | Baseline command observed 181 passed and 3 skipped out of 184 collected; optional Silero/Pipecat integration dependencies missing. No skips counted as passes. |
| Node logic tests pass | VERIFIED (execution) | `node --test tests/review_ui.test.cjs`: 3 tests, 3 pass, 0 fail. |
| Detection is English only | VERIFIED | `RuleExtractor.extract` returns no events when `segment.language != "en"`; English regular expressions, `rules-en-v4`. |
| Approval is simulated; no bank/phone control | VERIFIED within inspected implementation | `callgate/workflow.py`, `verification.py`, `review_transport.py`; README explicitly disclaims real bank/phone enforcement. |

## Corrections to earlier assistant claims

- The September research ZIP is stale. This snapshot contains a runnable implementation and evaluation artifacts. Do not overlay the old ZIP onto this repository.
- Live transcription, scoped simulation, receipt signatures and evidence graphs are PRE_EXISTING, not future event inventions.
- Separate role credentials do not prove independently enrolled people; self-approval remains possible in the baseline.
- Existing risk evidence is revision-aware, not a proven append-only ratchet. CHALLENGED can revert after a transcript revision; BLOCKED and COOLING_OFF are sticky. The event monotonicity work must respect that distinction.
- No registered-contact pairing, financial institution integration, dual-device independent identity, or production retention guarantee was demonstrated by this audit.

## README coverage comparison

No additional runnable capability was established as missing from README by this audit. Existing signed receipts, measurement persistence, English risk rules, revision handling and reviewer simulation are already described. Future capability tokens and enrolled contacts appear in older design documents, not current implementation claims.

No missing implementation was found behind the README's explicitly scoped current-feature rows. Limitations are documented. The stale outreach schedule is a documentation defect to repair, not proof of completed outreach. Historical Python passes must not be presented as current environment results.

## Integrity and audit limits

The renderer checks the raw archive hash. This audit did not modify raw.json, raw.sha256, labels or prediction rules. Generated report line endings may differ between operating systems and are restored to original CRLF when contents agree.

The claims registry now binds frozen pilot quantities, interval percentages, historical test quantities and source-level operational constants. Date/identifier/instruction digits are explicitly classified as nonmetrics. Unregistered or changed digit-bearing lines fail closed. Registration and source-literal checks are not proof of real-world effectiveness.

Legal consent, third-party retention, real phone capture, real transfers, and independent reviewers remain UNVERIFIED. Public demo hosting is not authorized.

## Current local increment (not part of the original source commit)

- `callgate/safety_policy.py` adds bounded Mandarin/mixed lexical extraction and a session-monotone safety-category ratchet. The live `DemoWorkflow` uses it; archived `Conversation` stays unchanged.
- The ratchet's minimal former failure is final `Send money.` followed by a revised `Hello.`: current evidence correctly disappears, but live CHALLENGED can no longer revert to UNVERIFIED.
- `POST /api/protected-action` returns forbidden with code `POLICY_PROOF_REQUIRED`; verified simulated completion remains a separate path.
- Reviewer denial, observed expiry, or exhausted challenge guesses latches session authorization refusal; changing amount/destination does not clear it. A explicitly fresh demo session clears it and is not a production identity boundary.
- `python -m scripts.proof_demo` demonstrates a forced empty detector plus a separately signed valid simulated completion. It uses generated local test keys, not independent enrolled humans.
- Prospective v2 inputs are synthetic text only with provisional author labels. They have not been passed to CallGate. Independent annotation remains pending.
- See BUILD_LOG for actual command outputs, denominators, skipped integration tests and remaining gaps. No new accuracy result replaces the frozen pilot.

## After the merged safety increment

The owner squash-merged the safety increment into main as `1882e3d` on 2026-10-06. The former pending-PR language in historical entries refers to the earlier audit, not current merge status.

The next increment adds trusted-startup claimed-identity routing, identity-bound operation commitments, recorded same-origin rejection, duplicate signing-key rejection, and scoped reviewer transport. Launcher contacts remain synthetic and ephemeral. Independently enrolled human identity and remote dual-device delivery remain unimplemented. See `docs/CONTACT_VERIFICATION.md` and the latest BUILD_LOG entry.

Owner merged that contact increment as `6855522` before the next work. The follow-up now connects multiple synthetic saved contacts to independent reviewer processes and scoped bearer routes. Actual loopback integration checks identity switching, cross-contact invisibility/refusal and valid completion. Different processes and keys still do not prove different humans.

Owner merged the multiple-contact increment as `7405a36` before the next work. The current follow-up changes the participant page into a simulated AI checkout surface without changing the protected-action/reviewer authorization path. It also adds optional Sentry observability hooks that are disabled unless `CALLGATE_SENTRY_DSN` is configured; tests verify sensitive transcript text, plain amounts, destinations and contact fields are omitted from emitted records. No real payment provider, Visa affiliation, committed DSN, Session Replay or external Sentry project evidence is present.

Owner merged the checkout-observability increment as `18f0cf1` before the next work. The current follow-up adds `evaluation_checkout`, a synthetic author-written safety-utility rehearsal for the simulated checkout surface. It compares deny-all, unguarded checkout and CallGate's existing simulated approval path with raw denominators. This is not independent annotation, real shopping telemetry, real payment execution or a replacement for the frozen v1 voice-risk pilot.

Owner merged the checkout rehearsal increment as `e176bd0` before the next work. The current follow-up adds a generated `evaluation_checkout/safety_utility.svg` figure from the same JSON results. It is a presentation artifact only; no new measurement, label source or payment integration is introduced.

The next checkout-evaluation follow-up adds an OTP step-up baseline and CallGate contact-availability/latency variants. In the author-written model, OTP step-up fails under coercion when the victim relays the code, and CallGate loses legitimate completion when a contact is unavailable. These are scripted assumptions for transparent comparison, not observed human behavior.
