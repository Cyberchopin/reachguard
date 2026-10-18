# Event Backlog

Every item below is a specification only. Implementation begins at the hackathon.

| ID | Priority | Issue | Acceptance evidence |
|---|---:|---|---|
| CG-001 | P0 | Define strict CallEnvelope schema | Fuzzed extra/forged fields rejected |
| CG-002 | P0 | Implement trust-state machine | Property tests for mandatory transitions |
| CG-003 | P0 | Build enforcement gateway | Direct protected calls return proof-required error |
| CG-004 | P0 | Create session-bound verifier | Expired, replayed, wrong-scope proofs rejected |
| CG-005 | P0 | Enforce secrecy breaker | Secrecy + high impact always enters cooling-off |
| CG-006 | P0 | Isolate parser identity/network/tools | Infrastructure and integration evidence |
| CG-007 | P1 | WebRTC two-party demo | Stable local call and prerecorded fallback |
| CG-008 | P1 | Stream STT into evidence segments | Timed segments with uncertainty and redaction |
| CG-009 | P1 | Human-first recipient card | User can explain pause and next action |
| CG-010 | P1 | Expert proof trace | Shows evidence → decision → enforcement → receipt |
| CG-011 | P1 | Append-only signed receipt | Public verification succeeds; mutation fails |
| CG-012 | P1 | TTL deletion behavior | Raw audio absent after configured TTL |
| CG-013 | P1 | Red-team harness | Core scenario matrix produces report |
| CG-014 | P2 | Acoustic deepfake sensor | Honest benchmark and inconclusive state |
| CG-015 | P2 | Agent-to-agent handshake demo | Unknown agent cannot exceed signed scope |
| CG-016 | P2 | Multilingual coercion support | Tested on declared languages only |
| CG-017 | P2 | Trusted Circle settings | Context-specific, revocable, private alternatives |
| CG-018 | P2 | Software supply-chain evidence | SBOM, dependency scan, signed release |

## Hard scope rule

P2 work starts only when CG-001 through CG-013 meet their evidence criteria. A polished detector cannot compensate for a bypassable enforcement boundary.

