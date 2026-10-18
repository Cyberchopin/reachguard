# Checkout safety-utility rehearsal

Synthetic author-provided checkout rehearsal. No real payments, no independent labels, no population claim. Contact availability and latency are scripted parameters.

| System | False execute | Legitimate completion | Median verify ms | P95 verify ms |
|---|---:|---:|---:|---:|
| deny_all | 0/3 (0.0%) | 0/3 (0.0%) | None | None |
| unguarded_checkout | 3/3 (100.0%) | 3/3 (100.0%) | 0 | 0 |
| otp_step_up | 3/3 (100.0%) | 3/3 (100.0%) | 12000 | 12000 |
| callgate_p100_fast | 0/3 (0.0%) | 3/3 (100.0%) | 24000 | 30000 |
| callgate_p67_observed | 0/3 (0.0%) | 2/3 (66.7%) | 21000.0 | 24000 |
| callgate_p67_slow | 0/3 (0.0%) | 2/3 (66.7%) | 84000.0 | 96000 |

![Safety-utility chart](safety_utility.svg)

Wilson intervals are included in the JSON for descriptive proportions only.
Reviewer timing is a synthetic parameter, not measured human response time.
Deny-all has no unauthorized execution in this rehearsal, but also no legitimate completion.
OTP step-up is modeled as failing under live coercion because the victim relays the code.
CallGate variants model contact availability and delay; lower availability creates conversion loss.
