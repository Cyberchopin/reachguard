# Signed confirmation prototype

The ConfirmationCoordinator creates bounded, expiring requests for a reviewer selected by trusted orchestration. The reviewer's public key is registered at startup; callers cannot supply a replacement key. The reviewer signs the exact request plus the approval/denial boolean using pyca Ed25519. The issuer checks stored request equality, time and signature before issuing one scoped demo credential. Rejected decisions close the request without issuing anything; invalid signatures do not consume it.

This is a Python service interface and test harness, not a human-facing confirmation product. The tests simulate a reviewer with a generated key. There is no passkey/login enrollment, separate-device UI, identity proofing, notification delivery, or real payment integration. No public confirmation endpoint is exposed. A valid reviewer signature does not establish that a real human reviewed the content.

Pending confirmations are process-local and bounded to 1,000 requests. Restart invalidates pending requests. Issued credentials can use the existing shared local SQLite replay ledger. Reviewer keys and signing keys must be persisted and controlled separately before a deployed confirmation flow is possible. Credentials are valid for 120 seconds from issuance. Signatures bind denial as well as approval; changing the boolean invalidates the signature.

This coordinator does not grant policy approval or lift the Guardian's latched states. The demo gate still requires trusted policy approval and confirmation inputs. Do not accept those booleans from unauthenticated HTTP JSON. The existing demo issuer helper remains test-only; do not expose it as an alternative public issuance route.

Eight tests cover signed approval through the persistent demo gate, request replay, wrong signer, signed scope changes, denial, expiration, coordinator restart, denial-bit tampering and concurrent confirmation (exactly one credential issued). Full local suite: 90 passed. GitHub workflow installs verification dependencies so these tests are not silently skipped there; remote CI has not been run in this step.

Next: implement an authenticated reviewer transport with a separate trusted display of the exact requested action, explicit approve/deny controls, and key enrollment/revocation. Select that identity mechanism before claiming independent human verification is complete.
