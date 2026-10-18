# Step 3 review gate: written answers

## 1. Dataset scale

60 is the current pilot size, not a final upper limit.
The proposed final target is 600 NEW, distinct scenario families:
200 scam, 200 benign lookalikes, 200 ambiguous; 50 per class per context.
Use the same four contexts. Allocate 60% dev / 40% test within each
context/class stratum using seed 20260916 before rendering variants:
360 dev and 240 test, including 80 test scam, 80 test benign and 80 test ambiguous.
These are planned counts, not existing data or computed performance.

Exclude all 60 pilot families and their paraphrases from the final corpus.
Do not inflate the sample size by changing names, numbers or places. Future
variants remain in their parent's split and do not count as independent families.
Keep the frozen pilot unchanged; create a separately versioned final dataset.

600 is a feasibility target, NOT a statistically powered sample-size claim.
Precision depends on predicted-positive count; category estimates will still
have small denominators. No desired interval width or deployment prevalence
has yet been agreed, so no claim of adequate statistical power is justified.
Do not expand the test set adaptively after observing performance.

If resources cannot support 600 genuinely distinct, reviewed families, publish
the actual smaller counts and label the work a pilot. Do not quietly replace
independent review with more same-author generated examples.

## 2. Independent reviewers

None are recruited or confirmed. There are no actual names to give.
The project assistant authored the scripts and has seen the engine; it cannot
serve as either independent reviewer. The developer who tunes the system must
not adjudicate or inspect the held-out calls.

Recruit two non-author reviewers able to apply the English rubric, plus an
independent adjudicator if necessary. A custodian, separate from tuning, handles
the held-out files. Record actual pseudonymous reviewer IDs, relevant experience,
relationship to the project, conflicts and completion dates once confirmed.
One person may hold more than one administrative role only if the resulting
loss of independence is explicitly disclosed; do not count them twice.

If reviewers remain unavailable, use this disclosure verbatim:

“This evaluation uses synthetic transcripts with provisional labels supplied by
the same project assistant that authored the cases and had prior access to the
CallGate implementation. Labels were not derived from CallGate predictions.
No independent human annotation, adjudication, or inter-rater reliability study
has been completed. A frozen holdout limits later tuning exposure but does not
establish author independence or real-world validity.”

Unrecruited reviewers remain an OPEN dependency. Writing a protocol does not
complete independent labeling. Do not call the dataset independently validated.

## 3. Binary output mapping

The complete machine-readable contract is prediction_mapping.v1.json.
Freeze this contract before baseline development and before any test prediction.

At the end of a call, map the deterministic Conversation state:

| State | Predicted positive |
|---|---|
| UNVERIFIED | 0 |
| CHALLENGED | 1 |
| COOLING_OFF | 1 |
| BLOCKED | 1 |

The measured classifier is CallGate's intervention signal used as a proxy for
scam screening. A positive is NOT proof of fraud; a negative is NOT proof of
safety. Legitimate calls triggering confirmation count as false positives against
benign ground truth, rather than being relabeled scam to flatter the system.

Use the final call state, not UI message emission or an adjustable score
threshold. Run a fresh Conversation for each call and feed all turns in order.
Use trusted synthetic roles as provided and report this as an oracle-role text
evaluation. Do not simulate reviewer approvals, inject consent/gate results or
invent ASR timing. Transcript ordering timestamps, if required by the API, are
synthetic placeholders and cannot supply any latency measurements.

Ground truth scam is 1, benign is 0. Ambiguous ground truth is retained outside
the binary confusion matrix, with its positive/negative/error counts and examples
reported separately. Never count ambiguous outcomes as automatically correct.
No classifier abstention is implemented in this contract.

Unknown states, exceptions or incomplete calls are execution errors, never
negatives or silently dropped samples. Any such error prevents a headline
complete-cohort metric; report error IDs/counts and completion coverage, fix the
execution issue under a documented rerun protocol, and disclose any exposure.
Missing labels or malformed input fail preflight before predictions.

Gate authorization success/refusal is a separate endpoint. Removing a confirmation
requirement must not be presented as a classification improvement if predictions
do not change. Later score-based PR curves are a secondary analysis and may not
replace this frozen primary operating point.

The hash ledger freeze.sha256.json binds the mapping and these answers.
Hashes detect changed bytes; they do not prove blinding, independent authorship,
an external timestamp or reproducibility of a yet-unwritten evaluator.
Any change requires a new version and an explicit disclosure.

## Review status

No baseline, performance evaluation, metrics or test predictions executed.
Stop here. Step 3 is not authorized by this document.
