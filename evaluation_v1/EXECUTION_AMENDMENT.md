# Explicit scope amendment, 2026-09-16

The owner instructed us to skip the independent-review step and complete the
remaining steps. This supersedes the Step 3 stop and independent-review release
gate for THIS 60-call unvalidated pilot only. It does not turn provisional
labels into independent ground truth or satisfy the 600-family target.
Original frozen files and hashes remain unchanged.

Every generated report, figure and resume draft carries the unvalidated-pilot
disclosure. The test set is revealed by the first run; do not tune against it
and later call it an untouched final test. Further improvements need new test
families. The custodian-only local raw files must be provided for reproduction;
they are not on GitHub merely because the code is.

## Fixed analysis before first predictions

Primary binary mapping remains frozen. Evaluate full CallGate and lexical baseline.
Ambiguous cases are excluded from binary metrics and reported separately.
Wilson 95% intervals for precision, recall, FPR and FNR; F1 interval obtained by
transforming the Wilson interval of TP/(TP+FP+FN) with f(q)=2q/(1+q).
Undefined denominators yield null. These are conditional working-model intervals
for this synthetic sample, not population coverage guarantees or real-world accuracy.
Calls are the resampling/analysis unit; there is one call per family.

Secondary PR curve: distinct final heuristic score thresholds on binary-labeled
calls, shown alongside the actual primary-state operating point. No threshold
is selected from test. Scores are not calibrated probabilities.

Evaluation-only ablations remove the credential BLOCKED rule, the secrecy
COOLING_OFF rule, or the sticky-state constraint, one at a time. Reuse the
production engine's event extraction, bookkeeping and scoring; an evaluation
subclass replaces only policy transition. Check the no-ablation subclass agrees
with the unmodified engine on all calls; otherwise fail the run.
No contradiction gate exists. Human approval is outside the transcript
classifier and is not modeled by this corpus; neither will receive invented
ablation performance. Report such requested experiments as unavailable.

Latency uses actual monotonic wall-clock deltas for input construction, production
engine ingest, and evaluation policy transition. Production ingest combines
extraction, risk scoring, state transition and snapshot construction; it is not
reported as isolated risk-scoring time. Transition time in the evaluation subclass
is separately named, not falsely attributed to production gate execution.
No ASR, phone network or actual confirmation API is called. Provider billing
is not applicable; total infrastructure cost and human review cost are unknown.
One pass, no warm-up, fixed file order, no outlier deletion. Histograms are
descriptive; do not infer bimodality or an SLA from 24 calls.

Failure groups are post-hoc diagnostic hypotheses, explicitly distinguished from
causally demonstrated findings. Include every error ID; quote up to three examples
per group, or all when fewer exist. Never fabricate additional examples to reach
a quota. No rule changes after opening test.

Capture exact environment and source hashes. Preserve first results. Replay
saved predictions/timings to regenerate exact figures and values; fresh timing
runs naturally vary and must not overwrite the first run.
