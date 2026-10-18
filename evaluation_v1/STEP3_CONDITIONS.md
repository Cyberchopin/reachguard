# Conditional Step 3 plan — 2026-09-16

## Recruitment: channels, owner and dates

Owner of external outreach: project owner. No invitations have been sent and no
reviewers are confirmed. The assistant will not contact people or spend money
without authorization.

Primary channel: the owner's UCLA/TASL classmates or research peers, approached
personally for reciprocal review work. Select two fluent English readers who
have not authored these cases, tuned CallGate or seen its predictions.
Fallback channel: Crystar teammates satisfying the same exclusion criteria.
These are proposed channels supplied by the owner, not verified available people.
Disclose any colleague relationship; this is independence from implementation,
not a claim of independent institutional certification.

By September 20, 2026 (America/Los_Angeles): owner sends invitations and records
responses, availability and conflicts. By September 23: obtain two explicit
acceptances, assign pseudonymous IDs and identify a non-tuning custodian.
If unconfirmed at that deadline, status becomes UNVALIDATED PILOT, not
“independent review in progress.” No paid fallback is assumed or authorized.
An external adjudicator is needed for disagreements the two reviewers cannot
resolve without developer access to held-out content.

## Workload and prospective downgrade

600 unique calls require 1,200 first-pass annotation judgments for two reviewers,
plus authoring, provenance checks and adjudication. These are workload counts,
not an estimated duration.

Before committing to the full expansion, record actual elapsed authoring and
review times on 12 NEW DEVELOPMENT families (one per context/class stratum).
These belong to the planned 360 dev calls, not an additional test pool.
No hours estimate is currently available. Estimate remaining workload only from
those observations, reporting sample size and excluding them from performance
evidence. If confirmed available reviewer time cannot cover the projected work
by October 7, shrink scope before generating the remaining corpus.

Cutoff: October 7, 2026, 23:59 America/Los_Angeles, before ANY test predictions.
The full target remains 600 new distinct families with 360 dev / 240 test.
If fewer than 600 valid families or fewer than 240 fully double-reviewed and
adjudicated test calls are ready, report a reduced-size PILOT with actual counts;
do not claim that the original target was achieved.

Minimum release gate for a reduced independently reviewed pilot: 120 resolved
test calls, including at least 40 scam, 40 benign and 40 ambiguous. These are
operational minimums, not a power calculation or guarantee of precision.
Do not relabel, substitute or discard cases to reach these counts; if adjudication
changes class balance below the gate, the gate fails. Preserve all omissions and
unresolved cases in an attrition ledger with reasons determined blind to output.

If below this minimum, publish development/protocol work only at this milestone,
with no headline held-out performance. Do not change the rule after predictions.
If no independent review is available, all outward-facing material must carry
the exact disclosure in REVIEW_DECISIONS.md before any future unvalidated test
run is considered. The current runner does not authorize or support such a run.

## Secondary severity analysis, preregistered

Keep the frozen binary mapping unchanged. Also report a ground-truth-by-state
table (scam/benign/ambiguous × UNVERIFIED/CHALLENGED/COOLING_OFF/BLOCKED).
For benign calls, report each intervention state's count and rate with the same
benign denominator. Separately report the fraction ending in BLOCKED.

Current meanings: CHALLENGED permits requesting scoped approval; COOLING_OFF
denies that request while recommending independent checking; BLOCKED denies
approval for sensitive-information requests. Neither hangs up or times out a call.

Prespecified illustrative burden weights:
UNVERIFIED=0, CHALLENGED=1, COOLING_OFF=2, BLOCKED=3.
Weighted benign intervention burden = sum(weights for benign calls) / N_benign.
This is an ordinal engineering proxy, not dollars, measured customer harm or
validated utility. Report the unweighted state table alongside it.
Sensitivity analyses use (0,1,1,1) and (0,1,3,5), all published regardless of
which looks better. These are chosen design constants, not estimated results.
If N_benign is zero the measure is undefined, not zero.

Primary severity observation is final call state, matching the binary contract.
Additionally report highest intervention reached and transitions per call so a
temporary severe intervention is not concealed by the final state.
Ambiguous calls remain a separate tier with no assigned true harm cost.

## Timing contract

Use time.perf_counter_ns deltas, actual elapsed wall time from a monotonic clock.
Time input parsing/validation, keyword matching and binary decision separately.
Record per-call total too, including overhead not attributed to the three stages.
The baseline has no confirmation gate: gate latency is null/not applicable,
never relabeled from the binary decision duration.

This is local text processing, not ASR/API/network/end-to-end voice latency.
Synthetic ordering timestamps are never used for timing. No API is invoked;
provider cost is not applicable and total infrastructure cost is unmeasured.
Record interpreter/platform, source/config/data hashes and individual samples.
Do not use a single DEV sanity pass as an SLA or a stable latency benchmark.
Later CallGate gate-transition instrumentation remains separate work.

## Authorization boundary

Allowed now: baseline implementation, local fixture tests, DEV sanity pass.
Forbidden now: test predictions, test tuning, headline evaluation metrics.
No final report, resume bullet, chart or external disclosure-compliance claim
has been produced by this step. Recruitment and annotation remain outstanding.
