# Authorization safety and user utility: prospective protocol

Status: protocol, NOT RESULTS. The only current runnable counterfactual proof is `python -m scripts.proof_demo`; it uses generated test keys. New-corpus inference waits for independently returned annotations and a frozen label snapshot.

## Systems to compare

- Deny-all simulator baseline.
- Keyword warning baseline plus explicitly specified action rule.
- LLM-as-authorization-judge research baseline, isolated from real credentials/tools.
- CallGate's deterministic policy and independently scoped simulator authorization.

All systems receive the same scenario input and controlled contact-response model. Failure to configure the LLM is recorded as unavailable, not as a zero-error model. No baseline may touch real money or secrets.

## Outputs and denominators

- `false_execute`: protected actions completed without valid scope-bound proof / all protected-action attempts; additionally report the rate restricted to unauthorized attempts.
- `legitimate_completion`: legitimate eligible requests completed / legitimate eligible attempts. Define eligibility before results; do not exclude refused cases after seeing outcomes.
- `warning_recall`: scam conversations warned before the marked action / scam conversations with valid labels.
- `false_warning`: benign conversations warned / benign conversations with valid labels.
- `verification_ms`: initiation to confirmed decision, with contact-response delay separately recorded as a simulated parameter.
- Latency median and tail values calculated from saved monotonic-clock samples; include censored/time-out trials rather than silently dropping them.

Report count pairs and Wilson intervals for proportions only when assumptions are stated. Translations and trivial variants are correlated: resample by family for uncertainty or present descriptive counts; do not pretend call-level Wilson intervals resolve dependence or author bias.

## Failure injection

- Final ASR words dropped or replaced with explicit homophone variants.
- Acoustic/semantic detector forced benign.
- Optional evidence extractor produces an empty result.
- Proof expired, replayed, wrong-session, wrong-resource or signature-tampered.
- Reviewer declines or response times out.
- Same principal controls participant and reviewer: document the current gap; a local role token cannot prove different people.

## Safety–utility figure

Horizontal axis: legitimate-request completion. Vertical axis: unauthorized execution. Show raw denominators next to each system and label simulated contact response. Deny-all should visibly have no completion, not be presented as the winning safe system.

## Freeze and publication

Save inputs hash, code commit, policies, model versions, first predictions, raw timings and all failures before computing summaries. Never overwrite the first-run raw artifact. CI public-claim checks must bind to that run. New live performance has no measured value yet and must stay blank rather than inherit the old pilot.
