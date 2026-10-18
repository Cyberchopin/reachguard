# Reviewer identity: minimum threat model

Status: design draft, not an implemented identity provider.

The current launcher now provisions a synthetic saved-contact route before the session. `ContactDirectory` binds claimed identity to a reviewer public key and trusted credential-origin record; the coordinator rejects a matching initiator origin and shared contact keys. Reviewer transport is scoped to its addressee. These implemented checks do not establish independent human ownership, revocation or remote device enrollment. See `CONTACT_VERIFICATION.md`.

Protect operation scope, approval authority, signing keys and one-time execution.
The participant and caller may be adversarial. The broker host, reviewer process
and both signing keys are currently trusted. Role URLs are bearer capabilities.
The participant generates the six-digit challenge; it is an additional possession
requirement, not a human identity credential.

| Attack | Current protection and residual risk |
|---|---|
| Repeated guesses | Three wrong responses cancel a request; issuance limited to 5/minute and 30/hour per workflow process |
| Cancel/reset and request again | Issuance budget survives reset, consent changes and cancellation; trusted process restart resets it |
| Approval for another operation/session | Signed scope and exact current-request binding |
| Repeated execution | Expiry and one-time consumption; keys and gate are ephemeral |
| Participant obtains reviewer capability and challenge | Self-approval remains possible |
| Host or reviewer compromise | Outside current protection boundary |
| Authentic reviewer makes a bad judgment | Signature does not establish correctness |
| Reviewer unavailable | No successful simulated execution without valid current approval |

Next implementation contract: reuse an identity provider with phishing-resistant
authentication. A trusted administrator enrolls a reviewer and known contact
independently of the caller. Bind authenticated reviewer principal to approval;
reject participant-principal equality server-side. Reauthenticate for approval,
bind operation digest and expiry, and check account/key revocation before execution.

Persist attempt budgets across workers/restarts before remote exposure. Specify
key rotation and account recovery without letting a participant enroll or recover
their own reviewer. Test stolen sessions, revoked accounts, cross-principal
approval, concurrent consumption and reviewer unavailability. Different accounts
still do not prove different humans: enrollment and collusion remain organizational
assumptions.
