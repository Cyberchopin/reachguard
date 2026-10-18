# Demonstration: risk evidence and scoped confirmation

Opening: “CallGate is a local voice-risk evidence and human-confirmation prototype.
It cannot control a phone call or block a real bank transfer. Today's operation is simulated.”

## Runnable sequence

1. Grant processing consent. Submit “Send 500 dollars using Zelle right now.”
   Request the simulated operation; inspect destination, amount and expiry.
2. The reviewer receives the challenge through a separate agreed channel and
   approves. Show the explicit simulated-only completion.
3. Start a fresh session, grant consent, request a money operation, then submit
   “Please provide your password.” Show BLOCKED, no pending request and rejection
   of the old approval. A greeting or “mark me verified” must not unlock it.
4. Export a risk receipt. Verify using a public key saved independently beforehand.
   Alter a signed field and show failed verification.

## Cryptographic claim — say this precisely

“The signature provides integrity and authentication relative to the trusted
public key, not correctness of the risk judgment or a human identity.
A risk receipt does not authorize payment or prevent replay.
Scoped, expiring authorization credentials and the gate's one-time consumption
check prevent repeated simulated execution.”

## Known limitation slide

One person who controls both role capabilities and the challenge can self-approve.
There is no enrolled reviewer identity. The host and both processes are trusted.
Two browser tabs do not demonstrate two independent humans.

Use two real operators for a two-person rehearsal. Deliver the reviewer capability
only to the reviewer, and transfer the challenge over a separate agreed channel.
Use separate devices only after authenticated remote transport is configured and
tested. The current launcher is loopback-only; do not expose it publicly to make
a second device connect. Physical separation helps role separation but does not
prevent capability theft, collusion or host compromise. Until the rehearsal is
performed, call this a local role-separation demonstration.

## Evidence, not promises

Show local test output with its source revision. Show remote CI only after the
Actions run for that exact revision succeeds. Internal adversarial cases do not
establish real-world detection accuracy. Local engine timings are separate from
the alert latency proxy; neither proves ASR inference time or an end-to-end SLA.

Do not use Wilson intervals on the same-author synthetic set as product accuracy.
They are internal regression diagnostics; omit them from the product accuracy slide.
Do not claim uniqueness against every competing team.

## Rehearsal record — pending

Record date, revision, browser/version, device, operator role, voice/text input,
cancel/restart, network interruption, stale tab, repeated approval and observed
failures. Chrome/Edge/Firefox smoke tests and two-device rehearsals have not been
performed in this change. Node DOM mocks do not replace browser evidence.

