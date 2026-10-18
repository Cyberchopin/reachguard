# CallGate: resume wording and interview evidence

## Resume body — recommended two bullets

- Built a streaming-speech risk prototype with a deterministic four-state policy, scoped approval for simulated actions, and replay-rejection tests; enforcement is limited to the local demo.
- Designed and executed a reproducible synthetic pilot with a frozen split, keyword baseline, policy-ablation harness and failure analysis on 24 test calls; labels remain author-provided and independently unvalidated.

Do not describe this as an LLM agent, six-state implementation, production
firewall, validated classifier or measured detection improvement.
“Blind-labeling protocol designed” is accurate; “blind labeling completed”
and “bias-resistant evaluation demonstrated” are not.
Keep the full report linked; the shorter resume wording does not replace its
disclosure or conceal a claim of superiority.

## Full disclosure

This evaluation uses synthetic transcripts with provisional labels supplied by
the same project assistant that authored the cases and had prior access to the
CallGate implementation. Labels were not derived from CallGate predictions.
No independent human annotation, adjudication, or inter-rater reliability study
has been completed. A frozen holdout limits later tuning exposure but does not
establish author independence or real-world validity.

## Interview: what actually runs?

“The live demo uses AssemblyAI for speech transcription. Risk extraction,
scoring and state decisions are deterministic Python rules; no LLM performs
risk judgment. The pilot bypassed speech entirely and measured local text
processing. I would describe this version as a streaming-speech risk and
authorization prototype, not an autonomous agent.”

ASR uses an external AI service in the live application. That does not make the
downstream risk classifier an LLM or make the text-only pilot an AI-inference
latency measurement. No paid provider was invoked during the pilot.

## Interview: how many states exist and what has been tested?

| State | Current implementation | Evidence scope |
|---|---|---|
| UNVERIFIED | Implemented | Observed in pilot; unit tests |
| CHALLENGED | Implemented | Observed in pilot; unit/integration tests |
| COOLING_OFF | Implemented | Cross-turn secrecy + high-impact and sticky-state unit tests; not observed in the 24-call test run |
| BLOCKED | Implemented | Credential-request and old-approval invalidation tests; user-reported microphone checks; not observed in the 24-call test run |
| VERIFIED_BOUNDED | Not a Conversation state | Earlier design terminology; scoped credentials are a separate mechanism |
| ESCALATED | Not a Conversation state | Earlier design terminology, not implemented in the current risk engine |

Do not claim six implemented states. Do not claim the two unobserved states
were never tested: fixture tests exist, but they are not held-out performance
evidence. The pilot observed 23 UNVERIFIED and 1 CHALLENGED; do not extrapolate
that observation to all 60 calls without separately examining development data.
BLOCKED prevents simulated approval; it does not hang up a phone call.

## Interview: what did the ablations show?

“All three policy ablations had zero binary-metric delta in this pilot. The
observed test traces did not exercise the relevant BLOCKED/COOLING_OFF or
revision-sensitive sticky behavior, so this experiment provides no estimate of
those gates' benefit. It does not establish that the gates are useless.”

The evaluation override code executed; relevant distinguishing conditions were
not exercised. That is different from saying no policy code ran at all.
Future gate validation needs a separate stateful scenario suite with revisions,
pending approvals, expiry, rejection and replay. Ordinary call-family counts
alone will not solve this coverage problem. Human-confirmation outcomes must be
evaluated as authorization outcomes, not forced into detection F1.

## Interview: did it beat the baseline?

“No. On 16 binary-labeled synthetic test calls, CallGate F1 was 22.2% versus
30.8% for the lexical baseline. I audited all seven scam misses and grouped
them into credential wording, payment wording, and access/coercion coverage.
Those are diagnostic hypotheses on author-labeled data, not independently
confirmed causal findings. I preserved the first run and retired the test set
from improvement claims.”

Eight additional ambiguous calls remained UNVERIFIED in both systems; that was
absence of matched rules, not successful ambiguity detection.

## Interview: what will resolve the annotation gap?

“No independent reviewers are confirmed yet. My recruitment plan is to approach
UCLA/TASL peers for reciprocal review by September 20, 2026, with Crystar peers
as a fallback, excluding anyone involved in implementation or case authoring.
The confirmation deadline is September 23. If I do not obtain two independent
acceptances, I continue to label the work an unvalidated pilot.”

These are proposed actions, not completed outreach. The project owner must
perform or explicitly authorize contact. Record actual acceptance, conflicts,
reviewer IDs and blind-review completion; a plan does not validate labels.
Keep the October 7 scope checkpoint from STEP3_CONDITIONS.md. The later owner
requirement governs any “final” claim: completed development, the 600-family
scope, independent review, then a fresh frozen test evaluation.
