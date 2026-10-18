# Ethics and Human-Factors Safety

## Moral premise

Fraud succeeds by converting care into a vulnerability. A person sends money not because they are unintelligent, but because the attacker has made love, fear, duty, or shame feel more urgent than verification.

CallGate should not “outsmart the victim.” It should change the environment so that a coerced moment cannot become an irreversible action.

## Five product principles

### 1. Protect without humiliating

Use calm, concrete language:

> This call asks for money and asks you to keep it secret. That combination is unsafe. No payment can be approved from this call. I can help verify the person through a number you already trust.

Never say:

> You are being fooled. This is obviously fake.

The second message invites defensiveness and asks the recipient to choose between the product and a loved one.

### 2. Do not require belief in AI

The user does not need to believe a deepfake score. The system says what it observed, what rule applies, and what safe action is available. Verification occurs through another channel.

### 3. Friction can be care

Convenience is not always the ethical optimum. For requests involving money, credentials, legal threats, medical emergencies, or secrecy, delay is a protective control. The delay must be proportionate and offer a visible path forward.

### 4. Preserve autonomy before crisis

Users configure protections while calm:

- Which actions always require independent verification
- Which people or services may help
- Which contacts must never be notified
- Preferred language, accessibility mode, and callback method
- Whether any audio may be retained

During a high-risk call, the system enforces the earlier decision rather than asking a distressed person to redesign policy.

### 5. No surveillance bargain

Safety does not justify collecting a lifelong archive of voices and relationships. Raw audio, full transcripts, and biometric templates are minimized, separated, time-limited, and opt-in where possible.

## Enforceable ethical invariants

Ethics must compile into product behavior:

| Ethical value | Enforceable requirement |
|---|---|
| Dignity | No blame labels; explain evidence and next safe step |
| Autonomy | User chooses escalation contacts in advance and can revoke them |
| Privacy | Raw audio deleted by default; no voiceprint enrollment by default |
| Non-discrimination | Acoustic score never decides guilt or blocks by itself |
| Safety | Secrecy + urgency + high-impact request forces separation and verification |
| Proportionality | Low-risk conversation remains possible; controls scale with potential harm |
| Contestability | User can inspect, challenge, and correct a decision receipt |
| Accessibility | Essential decisions work without technical jargon, fine motor precision, or perfect hearing |

## Vulnerable-user experience

The default view should not be a cybersecurity dashboard. It should show one decision at a time:

1. **What is being requested?** “Money is being requested.”
2. **Why did CallGate pause it?** “The caller also asked you not to tell anyone.”
3. **What happens now?** “No money will move. We will call the saved number for your grandchild.”

Optional details can reveal transcript evidence, model uncertainty, and receipts for technical users and judges.

## The secrecy breaker

For a consequential request, “do not tell your family/bank/police” is not merely another feature in a risk score. It changes the allowed state transitions:

```text
IF high_impact_request AND secrecy_pressure
THEN disallow in-session approval
AND enter COOLING_OFF
AND offer independent verification
```

This rule works even if the caller is human, the voice is real, and the deepfake detector reports nothing.

## Trusted Circle without paternalism

“Notify family” is not a universal safe action. A relative may be controlling, abusive, financially exploitative, or simply unwanted. Trusted Circle must be:

- Explicitly enrolled by the user
- Scoped by situation (financial, medical, general)
- Revocable and reviewable
- Able to include a bank advocate, social worker, lawyer, or friend—not only family
- Silent about unnecessary personal details
- Bypassable through a documented emergency-safety route, not an impulsive high-risk approval

## Dynamic family verification

A static family safe word can help but can also be overheard, phished, or reused. Prefer:

- A challenge sent to an enrolled device
- A callback to a saved number
- A dynamic, single-use phrase generated through a trusted channel
- A previously agreed question only as a fallback, never the sole control for a major transfer

## Deepfake evidence and fairness

Acoustic detectors may perform differently across languages, ages, disabilities, microphones, codecs, and unseen synthesis systems. Therefore:

- Report calibrated uncertainty and operating conditions.
- Measure false positives across varied speakers and channels.
- Never label a person “fraudulent” from acoustic evidence alone.
- Use `inconclusive` when the signal is poor.
- Design the safe path so a false positive creates a respectful challenge, not exclusion.

## Victim-centered storytelling

The family incident may motivate the project, but the public pitch should:

- Remove names, location, institution, and identifying details.
- Avoid reenacting the exact private conversation.
- Avoid displaying the loss as spectacle.
- Focus on the attack pattern and the protective design.
- State that the victim's trust and care were exploited; do not imply gullibility.

## Philosophical position

CallGate does not attempt to compute whether a voice is morally trustworthy. It separates **being heard** from **being authorized**. A caller can be listened to with empathy while their request remains technically incapable of crossing a high-impact boundary.

That separation is the project's human and technical thesis:

> **Compassion should remain open; authority should remain bounded.**

