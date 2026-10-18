# Step 1: synthetic dataset design, frozen before new tuning

This is a small pilot evaluation corpus, not a real-world accuracy benchmark.
The existing CallGate rules predate it. No claim of a historically untouched
model or independent authorship is possible: the assistant author has already
seen the implementation. No system output is used to assign scenario labels.

## Target definitions (written before generation)

The target is transcript-supported deceptive solicitation, NOT whether an action
deserves confirmation. A legitimate transfer can deserve confirmation without
being a scam. Do not map CHALLENGED to scam ground truth.

- scam: the scripted conversation explicitly supports a deceptive pretext for
  obtaining money, credentials or unauthorized access. A suspicious tone alone
  is insufficient. Each label needs a rationale tied to visible dialogue.
- benign: the conversation supports an ordinary legitimate purpose, even with
  anger, urgency, financial language or authentication discussion. A mere
  unsupported claim of legitimacy is insufficient.
- ambiguous: the available conversation cannot resolve legitimacy. Do not
  silently force these into either binary class.

These are provisional author labels, not independently adjudicated truth.
Step 2 must review this rubric and establish blind annotation/adjudication
before any final performance claim. Labels never contain expected CallGate
states, scores or predicted events.

## Sampling and split

Four contexts: bank, technical support, romance/personal relationships, government.
Each contains 5 scam, 5 superficially similar benign and 5 ambiguous families.
Total: 60 calls = 20 scam + 20 benign + 20 ambiguous.
This deliberately balanced sample does not estimate deployment prevalence.

Seed: 20260916. Stratify by context and provisional class. Shuffle the five
family IDs in each stratum using Python Random; assign 3 to dev and 2 to test,
BEFORE rendering transcript rows. Ratio 60:40: dev 36, test 24.
Each test class has 8 calls; binary scam/benign test population is only 16.
Intervals will therefore be wide. Expand with independently authored families
before making consequential performance claims.

One distinct script per family; no slot-filled variants or numeric substitutions
inflate the sample count. Future paraphrases must inherit their parent's split.
Structural checks reject duplicate normalized whole calls across splits.
Shared semantic conventions remain; group separation cannot establish independence.

## Holdout handling

Dev inputs and provisional labels are separate JSONL files. Held-out inputs,
labels and author source stay in the git-ignored scambench/heldout/private area.
The manifest publishes counts and SHA-256 hashes, not held-out transcripts.
Do not open that area or rerun authoring while tuning. Do not evaluate CallGate
on test until the rubric, baseline, thresholds and analysis plan are frozen.

This is procedural isolation, not cryptographic access control. The authoring
assistant knows all scripts. The user has not been shown the test transcripts.
For stronger independence, ask an external custodian to author/adjudicate and
hold a replacement final set. Any test inspection during tuning retires that
version as final-test evidence; do not silently reshuffle it.

## Scope and limitations

English text only; no audio, genuine ASR timing, transcription noise, speaker
attribution validation or real victims. Turns preserve conversational order;
no invented millisecond timestamps. No metrics, costs, predictions, baseline,
ablation or failure-analysis results are generated in Step 1.
Ambiguous examples remain a separate reported tier; their eventual scoring
policy must be preregistered in Step 2/4, not selected after seeing results.

The private generator and its source are retained for the later reproducibility
step. Exact source, rubric, output hashes and interpreter version are recorded.
Regeneration is a custodian action, not part of routine development tests.
