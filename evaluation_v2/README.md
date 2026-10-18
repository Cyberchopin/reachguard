# Prospective evaluation inputs

Synthetic text-only scenarios; no real audio or identifying personal information. These are prospective inputs, not new accuracy results. Labels were authored by an assistant with access to the implementation and are not independent.

Give reviewers only `blind/` and `ANNOTATION_GUIDE.md`. Do not send `author_labels.jsonl`, predictions, product rules or this repository. Family IDs group translations and variants and must not be split across tuning/holdout sets later.

No CallGate run is authorized against this corpus until independent labels return, disagreements are handled and a custodian freezes the label snapshot. `annotation_status.json` records the pending gate. No independent person has been recruited or verified by this work.

Run `python evaluation_v2/verify_inputs.py` to verify schema contracts, label links, exact duplicate scripts, counts and manifest hashes. This tool does not import CallGate or run any predictions. Source script expected states describe desired policy, not current model outputs. Surgical audio insertion and ASR-like text are scenario plans, not recorded acoustic evidence.

The caption-only variants are correlated scenarios, not independent samples. Wilson intervals based on independent calls would understate uncertainty; report family-clustered results or disclose correlation. Do not advertise these inputs as a validated benchmark.
