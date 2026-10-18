# Claimed identity and saved-contact verification

Implemented: trusted-startup contact routing for the local simulator. Not implemented: independent human enrollment, phone delivery, identity-provider authentication, revocation, or real payments.

## Run it

Run `python -m scripts.start_review_demo`. Startup creates a synthetic `saved-family` entry with the reviewer child's public key. To give the fictional identity a different identifier, run `python -m scripts.start_review_demo --contact-identity fictional-parent`.

For separate family and bank roles, run:

```bash
python -m scripts.start_review_demo --contact-identity saved-family --contact-identity saved-bank
```

The launcher prints a labeled entry for each contact. Give each fictional role its corresponding reviewer entry. Each reviewer process generates its own signing key and has its own bearer capability. The participant loads the directory and selects the claimed identity. Only that identity's reviewer sees the pending request. Switching the identity replaces the previous request and invalidates its signature and challenge. No request is sent to a different contact as a fallback.

The local launcher accepts up to four distinct synthetic identities, rejecting duplicate or invalid names before opening sockets. The default reviewer port applies to the first contact; additional contacts use operating-system-assigned loopback ports. Use the printed URLs. If any process stops, the supervisor stops the whole demo; it does not silently substitute another reviewer.

Open the printed participant and reviewer links on the trusted host. Grant processing consent, submit `Send money.`, click **读取已登记联系人**, select the caller's claimed identity, and request confirmation for a fictional amount/destination. The reviewer checks the displayed identity and operation, receives the challenge through the agreed separate demo channel, and approves or denies. Approval only completes a simulation.

Unknown or omitted identities are rejected in the launcher. There is no contact enrollment endpoint and speech cannot add keys. The identity selection is an explicit participant input; the system does not claim to extract identity reliably from a transcript.

## Binding and trust

`ContactDirectory` is supplied by trusted startup. Each `SavedContact` binds a stable identity identifier to a reviewer and a credential-origin identifier. Origins are enrollment records, not HTTP Origin headers, client JSON, or proof of physical device ownership. The coordinator rejects a contact with the same origin as the session initiator; it also rejects reuse of a signing key across saved reviewers.

The operation digest commits to destination, amount, currency and claimed identity. The signed confirmation includes that digest, session, selected reviewer, claimed identity, random request identifier, and expiry. The request identifier supplies fresh nonce material. The issuer only signs after a matching registered reviewer decision; the gate consumes the resulting credential once. Client-selected reviewers cannot override the directory route.

Denial and observed timeout prevent further authorization for that session, including identity or amount changes. Status and pending-request reads observe expiry and clear expired requests. An explicit new demo session is a new scenario, not a production way to rehabilitate a denied transaction.

The broker capability is scoped to its configured reviewer route; a request addressed to another contact is neither returned to it nor accepted from it. The reviewer UI also checks its expected addressee and the identity/operation commitment before signing.

## Boundaries

- Multiple synthetic saved contacts now have separate loopback reviewer processes and scoped bearer routes. Remote devices, independent human enrollment and phone delivery are not implemented.
- Startup generates both role entry URLs on the same trusted host. An operator may hold both. This increment rejects recorded same-origin credentials, not all self-approval by one human controlling different credentials.
- Startup enrollment records can be wrong. Account/key compromise, collusion, recovery, revocation and persistent authorization state remain unresolved.
- Restart invalidates ephemeral keys and pending requests. No claim of durable production denial across restart is made.
- Legacy programmatic coordinator instances without a directory remain available for archived tests and the protocol rehearsal. They do not acquire saved-contact guarantees; a claimed identity is rejected if no directory is configured.
- No predictions were run on prospective blind evaluation inputs and no new warning-coverage or legitimate-request utility metric is asserted.

## Verify

Run `python -m pytest tests/test_contact_binding.py tests/test_multiple_contacts.py tests/test_review_process.py -q -p no:cacheprovider`. These cover routing, same-origin rejection, wrong-key signatures, modified identity/session/resource/nonce, replay, expiry, denial, distinct reviewer capabilities, identity switching, invalid CLI provisioning, and actual loopback HTTP completion through separate reviewer processes.
