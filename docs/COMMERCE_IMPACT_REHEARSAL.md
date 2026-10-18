# Commerce impact rehearsal

This is a controlled checkout simulator for the sponsor-facing story. It is not
a product metric, a real-shopping study, an independent label set, or a fraud
prevalence estimate.

Run:

```bash
python -m evaluation_checkout.run
```

The script writes:

- `evaluation_checkout/results.json`: machine-readable rows, raw numerators and denominators, Wilson intervals for descriptive proportions.
- `evaluation_checkout/REPORT.md`: short human-readable table.
- `evaluation_checkout/safety_utility.svg`: two-axis figure for a pitch slide or Devpost screenshot.

## What it compares

| System | Behavior in the rehearsal |
|---|---|
| `deny_all` | Never completes a protected checkout. |
| `unguarded_checkout` | Completes every protected checkout attempt. |
| `otp_step_up` | Completes every checkout when the user relays a code; in coerced calls the attacker receives the OTP. |
| `callgate_p100_fast` | Uses the existing transcript, policy, challenge, reviewer signature and simulated gate path with all contacts available. |
| `callgate_p67_observed` | Same CallGate path, but one legitimate contact is unavailable. |
| `callgate_p67_slow` | Same availability as `callgate_p67_observed`, with slower response latency. |

## What the current result shows

The generated report makes the deny-all tradeoff visible: it can avoid
unauthorized simulated execution while completing no legitimate checkout. It
also makes the unguarded checkout tradeoff visible: it completes legitimate
requests but also completes unauthorized ones.

CallGate's result in this rehearsal depends on the synthetic scenario design,
simulated reviewer responses, contact availability and delay parameters. It
demonstrates that the same protected path can complete a legitimate,
reviewer-approved checkout while refusing scam-like or blocked cases. It also
shows conversion loss when a trusted contact is unavailable. It does not prove
real consumer conversion, real fraud prevention, or real contact response
timing.

## Allowed pitch wording

"We added a reproducible checkout rehearsal that reports safety and utility
together, so a deny-all gate cannot look successful just because it blocks
everything."

"The chart plots false execution against legitimate checkout completion from
the generated JSON, not from hand-entered slide numbers."

## Not allowed

- Do not claim a payment network integration.
- Do not claim the numbers are real-world accuracy.
- Do not claim independent labels or human-response measurements.
- Do not compare this author-written rehearsal to the frozen v1 voice-risk pilot.
- Do not hide that CallGate utility depends on contact availability and response delay.
