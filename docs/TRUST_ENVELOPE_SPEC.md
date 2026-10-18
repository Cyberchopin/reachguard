# CallGate Trust Envelope — Draft Specification

**Document status:** pre-implementation interface design  
**Protocol version:** `0.1-draft`

## 1. Purpose

The `CallEnvelope` is a one-way contract between the untrusted analysis plane and the trusted control plane. It carries observations and claims, never authority.

## 2. Conceptual envelope

```json
{
  "protocol_version": "0.1-draft",
  "session_id": "opaque-random-id",
  "observations": {
    "language": "en",
    "transcript_segments": [],
    "channel_signals": [],
    "acoustic_signals": []
  },
  "claims": [
    {
      "subject": "caller",
      "predicate": "claims_identity",
      "value": "family_member",
      "evidence_refs": ["segment-4"]
    }
  ],
  "requested_capabilities": [
    {
      "action": "transfer_money",
      "resource": "unspecified",
      "parameters": {"amount": "unknown"},
      "evidence_refs": ["segment-9"]
    }
  ],
  "coercion_signals": [
    {
      "type": "secrecy_pressure",
      "confidence": 0.0,
      "evidence_refs": ["segment-7"]
    }
  ],
  "uncertainty": [],
  "parser": {
    "model_id": "event-selected-model",
    "schema_version": "0.1-draft"
  }
}
```

## 3. Trust rules

- `session_id` is assigned by ingress, never by the model.
- The parser may populate observations, claims, requested capabilities, coercion signals, and uncertainty.
- The parser may not populate `verified_identity`, `authorization`, `policy_decision`, or `capability_token`.
- Every claim and signal must reference immutable evidence IDs.
- Unknown values remain `unknown`; they are not inferred to be safe.
- Unknown enum values and additional fields cause rejection.
- Text is length-limited, normalized, and treated only as data.

## 4. Independent verification record

This record is created only by the trusted verifier:

```json
{
  "session_id": "opaque-random-id",
  "challenge_id": "opaque-challenge-id",
  "method": "known_channel_callback",
  "subject": "enrolled-contact-id",
  "status": "VERIFIED",
  "verified_capabilities": ["continue_conversation"],
  "issued_at": "RFC3339 timestamp",
  "expires_at": "RFC3339 timestamp",
  "nonce": "single-use-random-value",
  "verifier_signature": "detached-signature"
}
```

Identity verification and capability authorization are separate. A verified family member may still lack authority to request access to money, codes, or private records.

## 5. Policy input

The policy decision point receives exactly:

- Validated `CallEnvelope`
- Verified, signed challenge results
- Preconfigured user policy by opaque ID
- Requested capability classification
- System health and dependency status
- Policy version and current time

It does not receive raw audio.

## 6. Decision object

```json
{
  "session_id": "opaque-random-id",
  "decision": "COOL_OFF",
  "reason_codes": [
    "HIGH_IMPACT_FINANCIAL_REQUEST",
    "SECRECY_PRESSURE",
    "IDENTITY_UNVERIFIED"
  ],
  "allowed_next_steps": [
    "KNOWN_CHANNEL_CALLBACK",
    "CONTACT_USER_SELECTED_ADVOCATE"
  ],
  "prohibited_capabilities": ["transfer_money", "share_otp"],
  "policy_version": "event-build-version",
  "expires_at": "RFC3339 timestamp",
  "decision_signature": "detached-signature"
}
```

## 7. Capability lattice

| Impact | Identity/authority | Maximum decision |
|---|---|---|
| Conversational | Unknown | Listen and summarize |
| Low, reversible | Challenged | Ask clarifying questions |
| Sensitive disclosure | Independently verified | Bounded, confirmed disclosure |
| Financial/legal/account action | Unknown or voice-only | Cool off or block |
| Financial/legal/account action | Verified identity, unclear authority | Escalate |
| High, bounded, reversible | Verified identity and authority | Explicit confirmation then one-time token |
| Irreversible or outside demo policy | Any | Block or external human process |

## 8. Mandatory policy precedence

The following outrank all model confidence and user-interface requests:

1. `secrecy_pressure + high_impact` → `COOL_OFF`
2. failed/expired verification → no capability token
3. missing policy or enforcement health → fail closed for protected capability
4. parser-requested trust mutation → reject envelope and flag injection
5. mismatched session, nonce, or scope → reject

## 9. Agent-to-agent extension

An AI caller can present:

- Cryptographic agent identity
- Sponsoring principal
- Requested capability
- Purpose and data-use declaration
- Expiry and callback endpoint

CallGate verifies these as protocol evidence, then applies the same bounded policy. It never treats “I am an AI agent from Company X” as self-authenticating.

## 10. Privacy profile

- No raw audio in the envelope.
- Transcript evidence has a short TTL and can be replaced by salted hashes after review.
- Relationship labels should be coarse (`family_member`) unless detail is necessary.
- Receipt export must support selective disclosure.
- Secrets, OTP values, account numbers, and payment destinations are redacted before telemetry.

