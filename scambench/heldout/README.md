# Private held-out evaluation

An independent annotator should create two files outside the public repository:

- `inputs.jsonl`: dialogue segments plus case metadata, without answer fields.
- `labels.json`: an object keyed by case ID containing `benign`, `expected_events`, `expected_state`, and optional `expected_alert` and `risk_onset_ms`.

Each input case needs `annotation.author_id`, `annotation.authored_at`, and `annotation.source`. Use a pseudonymous author ID; do not put victim identity or private call text in Git. Consent and retention must be handled before using real recordings.

Place private files under `scambench/heldout/private/`, which Git ignores. Validate the split:

```powershell
python -m scripts.check_scambench_split --inputs scambench/heldout/private/inputs.jsonl --labels scambench/heldout/private/labels.json
```

After freezing both file hashes, run the blind evaluation:

```powershell
python -m callgate.bench --dataset scambench/heldout/private/inputs.jsonl --labels scambench/heldout/private/labels.json --output scambench/heldout/private/results.json
```

The validator rejects visible labels and normalized transcript overlap with the development set. It reports hashes so the tested files can be identified later. These checks reduce accidental leakage; metadata and hashes cannot prove that an author was independent or that labels were correct.
