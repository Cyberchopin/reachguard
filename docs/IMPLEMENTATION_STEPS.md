# CallGate incremental acceptance plan

Overall mathematical framework: [MATHEMATICAL_FRAMEWORK.md](MATHEMATICAL_FRAMEWORK.md). Current scope is a structural prototype; probabilistic models and real human identity enrollment remain future work.

## Step 1 — evidence provenance (implemented 2026-09-09)

NetworkX 3.4.2 constructs a session-local directed graph of current transcript revisions, extracted events and committed risk categories. Request `POST /v1/replay?include_graph=true` with the normal replay body. The default response stays unchanged. This is a replay API feature, not yet a live graph UI.

Graph nodes omit transcript text; spans reference the caller's supplied transcript. This omission does not anonymize all metadata. Nothing is persisted by this projection. Client-supplied graph edges are not accepted. Unknown speaker roles remain unknown; no real-person identity nodes are inferred. A graph is a provenance view, not a trained fraud detector.

Revision replacement removes superseded evidence from the current graph. BLOCKED/COOLING_OFF can remain latched by existing policy after correction; graph metadata explicitly distinguishes that policy history from current evidence. Full historical proof receipts are not implemented.

Fixed event extractor metadata to use rules-en-v3, matching the actual extractor. Tests verify provisional evidence, revision replacement, isolated sessions, detached output, missing raw text, valid edge endpoints and latched state. Full suite: 50 passed, 3 upstream deprecation warnings.

NetworkX is consumed as a pinned library dependency, not copied source. Upstream: https://github.com/networkx/networkx ; license: https://github.com/networkx/networkx/blob/networkx-3.4.2/LICENSE.txt (BSD-3-Clause). No new hosted fork created.

## Step 2 — independently signed verification (local prototype implemented)

See VERIFICATION_DEMO.md and CONFIRMATION_PROTOCOL.md: Ed25519 credentials, opt-in SQLite replay persistence and signed reviewer confirmation are implemented and tested. Full local suite reached 78 passing tests. Reviewer identities are simulated; no real login or confirmation transport is connected.

Define the trusted issuer registration boundary, action scope, expiry and session binding before using cryptography. Acceptance: invalid signatures, wrong issuer, altered scope, cross-session reuse, expiry and concurrent replay rejected. Only a simulated protected action; signing a caller's own statement does not verify it.

## Step 3 — semantic extraction and uncertainty

Preserve evidence spans and strict schemas. Add independently labeled paraphrase/quotation/role cases; compare against the current English heuristic. Report misses and false alarms, not just passing developer tests.

## Step 4 — probabilistic and graph model experiments

Use separate experimental dependencies and held-out time/entity/script-family splits. Require calibration and latency evidence before any user-facing probability. Model outputs cannot authorize protected actions.

## Step 5 — real-time reliability

Resolve local service egress permissions and test full audio chain under disconnect, delay, silence and correction. Current unit tests do not establish microphone/network availability. No browser demo restart was performed in step 1.
