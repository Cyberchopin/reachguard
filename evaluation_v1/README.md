# CallGate evaluation: unvalidated synthetic pilot

This evaluation uses synthetic transcripts with provisional labels supplied by
the same project assistant that authored the cases and had prior access to the
CallGate implementation. Labels were not derived from CallGate predictions.
No independent human annotation, adjudication, or inter-rater reliability study
has been completed. A frozen holdout limits later tuning exposure but does not
establish author independence or real-world validity.

Read pilot_results/REPORT.md for actual results, failures, ablations, figures and
resume drafts. The owner explicitly waived independent review for this pilot in
EXECUTION_AMENDMENT.md. The 600-family expansion was not performed.

## One-command reproduction

From the repository root, with the recorded Python environment:

    python -m evaluation_v1.evaluate_pilot render

This regenerates every published metric, example table and SVG from the archived
raw calls, labels, predictions and actual clock measurements in pilot_results/raw.json.
It verifies the raw file hash first. No fresh predictions or clock measurements
are needed. Figures include the disclosure and contain their own title/description.

To repeat inference and measure new timings, use a separate checkout, install the
repository requirements-lock.txt, and supply the original manifest-matching private
raw files; then run:

    python -m evaluation_v1.evaluate_pilot run

The run refuses to overwrite an existing raw.json. Fresh timing measurements are
not bitwise reproducible; compare predictions separately from timing variability.
Exact original Python, OS and installed package versions are recorded in raw.json.
The package list describes the observed environment, not a portable cross-OS lock.
The original evaluator source is archived as evaluator_at_first_run.py; later
renderer changes only organize failures and show deltas, not rerun predictions.

## Limits that must travel with the results

- 24 test calls: 8 scam, 8 benign, 8 ambiguous; 16 enter binary metrics.
- The test set is now revealed and retired for tuning-free final validation.
- Provisional author labels; interval calculations do not correct author bias.
- Actual local text timings only; isolated production scoring/gate timings,
  real voice latency and infrastructure costs are unavailable.
- Three evaluation-policy ablations exist. Contradiction and human-confirmation
  experiments are not supplied because the required feature/outcomes are absent.
- Failure groups are post-hoc explanations; they are not independently verified
  causal attribution. No fixes were made to detection rules from these failures.

Do not describe this as industrial readiness, real-world accuracy, an independent
benchmark, or evidence of superiority over the lexical baseline.
