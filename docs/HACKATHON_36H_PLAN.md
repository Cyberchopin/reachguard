# LA Hacks 36-Hour Build Plan

## Winning constraint

Build one incontestable security boundary and one unforgettable human story. Do not spend the event creating a telecom platform, training a foundation model, or integrating real payments.

## Definition of done

A scripted or live WebRTC caller speaks a coercive, prompt-injected request. The receiver sees an accessible explanation. The parser is visibly compromised or challenged, but the deterministic enforcement layer still prevents the simulated protected action, starts a known-channel verification, and produces a signed receipt.

## Timeline

| Time | Build slice | Exit condition |
|---|---|---|
| T−30 days | Public research only | Tag `pre-hackathon-research-v1`; no runtime code |
| 0–2 h | Boundary and repository start | `BUILD_LOG.md`, event branch, roles, sponsor decision |
| 2–6 h | Contracts and state machine | Schema, five trust states, invariant tests green |
| 6–10 h | WebRTC audio path | Two browsers exchange audio; frames have TTL |
| 10–15 h | STT + isolated parser | Transcript becomes validated envelope; no tools/egress |
| 15–20 h | Policy + enforcement | Direct and injected protected calls rejected |
| 20–24 h | OOB verification | Known-channel simulation with nonce, scope, expiry |
| 24–28 h | Human-first UI | Elder mode and expert trace show same decision |
| 28–31 h | Acoustic sensor | Add only if stable; always label probabilistic/inconclusive |
| 31–33 h | Red-team evidence | Run core matrix; export honest report |
| 33–35 h | Demo hardening | Local fallback, seeded scenario, receipts, video backup |
| 35–36 h | Submission | README, disclosure, credits, final three-minute rehearsal |

## Critical path

1. State machine and enforcement
2. Schema-isolated parser
3. Independent verification
4. Human-first interface
5. Evidence package
6. Acoustic deepfake sensor only after the boundary works

If time slips, remove the detector before removing the policy boundary.

## Team allocation

For a solo build:

- Use WebRTC, not PSTN.
- Use one model and one verifier.
- Use a simulated protected tool.
- Make the state-machine trace the main visual.
- Pre-record the attacker side as a consenting fictional voice.

For 2–4 people:

- Systems: policy, enforcement, tokens, receipts
- AI/audio: STT, parser isolation, optional acoustic sensor
- Product: accessible UI, verification flow, user testing
- Story/reliability: red team, evidence, deployment, pitch

## Scope cuts

Cut in this order:

1. Real PSTN integration
2. On-device model optimization
3. Multiple deepfake models
4. Organization directory integration
5. Full A2A protocol
6. Multi-language UI beyond the two best-supported languages

Never cut:

- No-tool parser boundary
- Deterministic enforcement
- Independent verification for protected actions
- Secrecy/urgency cooling-off rule
- Clear privacy behavior

## Sponsor adaptation

Re-check the final sponsor challenges at event start. Adapt infrastructure, telemetry, networking, or agents only if the integration strengthens the core story. Do not distort CallGate into a sponsor demo with no safety thesis.

## Reliability checklist

- Local prerecorded audio fallback
- Seeded transcripts if STT/network fails
- Deterministic policy works fully offline
- Simulated verifier fallback with visible “DEMO” label
- No real money, contacts, secrets, or family voice data
- One command or button to reset the demo
- Frozen known-good deployment before pitch
- Video backup of the complete flow

