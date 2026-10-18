# Signed decision receipt prototype

`callgate.receipt` reuses pyca Ed25519 to sign a minimal snapshot of a local decision. The payload binds receipt/session IDs, timestamp, policy and extractor versions, state, heuristic score and a SHA-256 digest of current finalized evidence metadata. It fixes `protected_actions_allowed=false` and labels the score as `heuristic_not_probability`.

The receipt omits transcript text, event confidence and provider speaker labels. The evidence digest covers segment ID/revision, event kind/span and extractor. This reduces retained content but does not make all metadata anonymous. It neither commits to the original transcript bytes nor proves the evidence or decision true. A party holding the source transcript can separately verify spans only if a future protocol explicitly binds a privacy-reviewed transcript commitment.

Verification checks the Ed25519 signature and expected session. Key distribution, rotation, revocation, durable receipt storage, monotonic time and public verification are not implemented. The signing key is supplied by trusted orchestration; no issuing HTTP route exists. Receipts are independent snapshots rather than an append-only chain.

Seven tests cover valid minimal receipt, field tampering, forbidden allow-state, wrong key, cross-session use and transcript revision replacement. This is an audit primitive, not an authorization credential and not a fraud verdict.
