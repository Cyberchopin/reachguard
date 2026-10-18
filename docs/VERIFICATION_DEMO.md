# Independent verification credential prototype

Implemented 2026-09-09. Install `pip install -e '.[verification]'` or the pinned requirements-verification.txt in the existing environment.

Reuses [pyca cryptography](https://github.com/pyca/cryptography) 46.0.5 Ed25519 signing and verification. No elliptic-curve arithmetic is implemented by CallGate. Retain upstream dependency licensing; cryptography is available under Apache-2.0 OR BSD-3-Clause (see upstream LICENSE).

CallGate adds strict credential fields, domain/version separation, deterministic serialization, issuer lookup, session/resource binding, a maximum 300-second lifetime, policy and confirmation prerequisites, and atomic one-time consumption within a single gate instance. The only supported action is simulate_protected_action. No real action is executed. The demo issuer does not perform independent identity verification.

Interface: issue_for_demo(private_key, issuer=..., session_id=..., resource=...) produces a SignedVerification; DemoVerificationGate(trusted_issuers).execute checks it with the expected session/resource and trusted policy/confirmation inputs. Do not expose those approval booleans or issuer registration to untrusted caller JSON. No public issuing HTTP route is added. Current audio Guardian remains advisory and cannot unlock this gate.

Acceptance: 15 added test cases, including wrong signing key, altered fields, unknown issuer, wrong scope, invalid time, missing confirmation/policy, replay and 16 concurrent attempts with exactly one success. Full local suite: 65 passed. Minimal environments skip this optional module unless cryptography is installed.

Durable mode: pass `replay_store=SQLiteReplayStore(local_database_path)` when constructing DemoVerificationGate. SQLite transactions and the unique (issuer, nonce) primary key serialize consumption across independent connections on one host. Records survive process exit and are not automatically pruned. Only issuer and nonce are stored, not transcripts or private keys. Without this argument the original disposable in-memory mode remains in effect.

Five added tests cover store reopening, separate-process consumption, concurrent independent connections, expiry and storage failure. Full local suite: 70 passed. This is not a multi-host or real-payment deployment test.

Limits: trusted clock, local database access controls, storage monitoring, registered/revocable issuer keys, actual independent verification and a trusted human confirmation channel remain required. Database deletion or restoration of an older backup requires invalidating previously issued credentials. Retaining nonces prevents consumed credentials becoming reusable after clock rollback, but does not make an unconsumed expired credential immune to a wrong clock. A crash after consumption may lose the simulated response; this gate provides at-most-once admission, not exactly-once execution of external actions. A valid signature establishes a key's endorsement, not the truth of a caller's identity claim.

## Accurate project narrative

The mathematical contribution is explicit modeling and checked invariants: provenance as a directed graph; credential validity as a conjunction of independently checked constraints; nonce consumption as a single state transition under concurrency. Probability calibration and ZK remain planned work, not delivered features. Attribute NetworkX and cryptography rather than claiming their algorithms as original research. Interview/resume wording should describe the aspects the student personally understands, designed and validated, with AI assistance disclosed when relevant.
