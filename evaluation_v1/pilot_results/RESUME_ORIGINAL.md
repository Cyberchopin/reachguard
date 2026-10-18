## Resume draft — limitations must remain attached

This evaluation uses synthetic transcripts with provisional labels supplied by the same project assistant that authored the cases and had prior access to the CallGate implementation. Labels were not derived from CallGate predictions. No independent human annotation, adjudication, or inter-rater reliability study has been completed. A frozen holdout limits later tuning exposure but does not establish author independence or real-world validity.

- Implemented a voice-risk screening prototype evaluated on 16 binary-labeled synthetic held-out calls plus 8 ambiguous calls; obtained precision 1.0000 and recall 0.1250 against same-author provisional labels, without independent validation.
- Compared a lexical baseline with three isolated policy ablations on 24 synthetic calls, reporting intervention severity separately from binary predictions; findings are limited to an unvalidated text-only pilot.
- Instrumented actual local call-processing durations for 24 test calls and preserved per-call traces and reproducible figures; measurements exclude ASR, telephony, isolated production gate latency and unmeasured infrastructure cost.
