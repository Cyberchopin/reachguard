# Step 2: blind labeling protocol v1

Status: protocol ready; independent annotation and adjudication NOT performed.
The Step 1 author labels remain provisional and frozen. This protocol does not
retroactively make them independent. The target definitions in DESIGN.md were
written before author labels were generated. This operational protocol is
written afterward and before any evaluation or new tuning.

## 1. What is being labeled

Unit: the complete supplied call, preserving speaker roles and turn order.
Target: whether visible dialogue supports a deceptive solicitation of money,
credentials or access. This is a synthetic transcript interpretation task,
not forensic proof that a real caller is a criminal.

Risk requiring caution, scam intent, and permission to execute an operation are
different targets. An ordinary legitimate payment can merit human confirmation.
Do not label it scam merely because CallGate would challenge it.

No external lookup, engine output, model score, author label, family name,
split membership, file ordering hint or expected policy state is shown to a
reviewer. They receive an opaque case ID and transcript turns only.

## 2. Decision rubric

SCAM requires both:
1. A request to obtain money, credentials, sensitive access or equivalent benefit.
2. Transcript evidence of deception or misuse: for example a material identity
   contradiction coupled with insistence on payment, a purported institution
   demanding a personal payment channel while evading independent checking,
   or an explicitly unauthorized credential/access request.

Politeness, anger, urgency, affection, gift-card vocabulary, an unknown caller
or a financial topic alone does not satisfy both requirements. A caller's claim
to be legitimate is not corroboration. If the context needed to interpret an
apparent contradiction is missing, use AMBIGUOUS.

BENIGN requires a coherent ordinary purpose and sufficient supporting context
in the transcript: an independently initiated known-channel interaction, an
existing matching transaction, or an ordinary bounded request without signs of
deceptive extraction. A recipient's statement of independent checking can count
as scripted evidence, not as an externally verified fact. Unsupported reassurance
by the caller alone cannot establish a benign label.

AMBIGUOUS applies when:
- intent or authorization is unresolved;
- corroboration is absent or materially conflicting;
- both legitimate and deceptive explanations remain plausible;
- the transcript is insufficient or internally incoherent.

Record uncertainty instead of guessing the author's intended category.
Do not equate AMBIGUOUS with an annotator forgetting to finish the form.
Incomplete forms must be returned for completion.

## 3. Required annotation record

For every case record: case_id; anonymous reviewer_id; label (scam, benign,
ambiguous); rubric_version; evidence spans (turn index, exact quote);
one-sentence reasoning that connects the evidence to the rubric; alternative
interpretation; and uncertainty note. At least one span is required, including
for ambiguous cases. Do not quote information absent from the transcript.

An evidence span is not a predicted event label. No expected state, score,
threshold or CallGate output is permitted in the annotation packet.

## 4. Independent review and adjudication

Use two human reviewers who did not author the examples, blinded to each other's
labels and to all system outputs. Disclose if suitable independent reviewers
are unavailable; do not substitute two prompts to the same author and call that
independence. The authoring assistant is not an independent reviewer.

A custodian distributes all calls in a fixed shuffled order, with split and
category metadata hidden. The developer/user reviews only development calls.
The held-out portion is handled by reviewers/custodian outside the tuning loop.
Do not send the held-out packet to the developer to resolve disagreements.

Agreeing labels with adequate evidence are accepted. Disagreements go to a
third reviewer, also blinded to predictions, who records their own judgment
before viewing the two rationales. Record the resolution and reason; unresolved
cases remain ambiguous. Preserve both original labels and the adjudication.

Report the full 3-by-3 annotator agreement table, raw agreement and class counts.
If later calculating kappa, also report marginals and degenerate cases; agreement
does not establish correctness. No agreement statistic has been computed yet.

## 5. Freeze and changes

Complete rubric clarification using DEV only, before reviewing test labels or
running test predictions. If the rubric changes, version it, preserve the old
records, and have reviewers relabel all affected calls while still blind.

Do not silently change provisional author labels in the frozen Step 1 files.
Store independent annotations and final adjudicated labels as new artifacts.
Publish their hashes and actual dates once they exist. Keep the original
split fixed even if adjudication changes class balance; report the resulting
imbalance. Never discard hard cases or rebalance after seeing model errors.

If test text or labels enter tuning, retire that test version for final claims.
Collect a new independent final set rather than pretending a reshuffle restores
independence. Hashes detect file changes, not human exposure or secret tuning.

## 6. Reporting boundary agreed before evaluation

Binary scam/benign metrics will exclude ambiguous ground truth ONLY with explicit
coverage and counts reported alongside them. The ambiguous tier must have its
own prediction/action distribution and qualitative analysis. Do not score an
ambiguous case as correct merely because the system is cautious.

Policy refusals and human-confirmation gates are separate outcomes from scam
classification. Later ablations must distinguish detection metrics from action
authorization outcomes. A gate that does not alter classification cannot
legitimately claim a precision gain. Mapping system output to binary predictions
and any abstention policy must be fixed in the later baseline/metrics steps.

No precision, recall, agreement, confidence interval, cost or latency number is
claimed by this protocol. All such results require actual later computations.

## Completion checklist

- [x] Pre-generation target definitions in DESIGN.md.
- [x] Operational blind-review and adjudication protocol written.
- [x] Provisional labels kept separate from transcript inputs.
- [ ] Independent reviewers assigned.
- [ ] Two blind annotation passes completed.
- [ ] Disagreements adjudicated; label artifact hashes frozen.
- [ ] Inter-reviewer agreement computed from actual annotations.

Step 2 protocol is ready for review; the annotation work remains outstanding.
