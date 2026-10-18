from concurrent.futures import ThreadPoolExecutor
import pytest
pytest.importorskip("cryptography")
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from callgate.confirmation import ConfirmationCoordinator, ReviewerDecision, decision_bytes
from callgate.verification import DemoVerificationGate
from callgate.replay_store import SQLiteReplayStore


def setup():
    issuer, reviewer = Ed25519PrivateKey.generate(), Ed25519PrivateKey.generate()
    coordinator = ConfirmationCoordinator("issuer", issuer, {"reviewer":reviewer.public_key()}, clock=lambda:1000)
    request = coordinator.create(session_id="s", resource="r", reviewer="reviewer")
    def sign(approved=True, key=reviewer, req=request):
        return ReviewerDecision(request=req, approved=approved, signature=key.sign(decision_bytes(req, approved)).hex())
    return issuer, coordinator, request, sign


def test_confirmation_to_persistent_gate(tmp_path):
    issuer, coordinator, request, sign = setup()
    credential = coordinator.decide(sign())
    gate = DemoVerificationGate({"issuer":issuer.public_key()}, clock=lambda:1001,
                               replay_store=SQLiteReplayStore(tmp_path/'replay.sqlite3'))
    args = dict(session_id="s", resource="r", human_confirmed=True, policy_allows=True)
    assert not gate.execute(credential, **args)["real_action_executed"]
    with pytest.raises(ValueError): gate.execute(credential, **args)
    with pytest.raises(ValueError): coordinator.decide(sign())


def test_forged_reviewer_does_not_consume_request():
    _, coordinator, _, sign = setup()
    with pytest.raises(ValueError, match="signature"):
        coordinator.decide(sign(key=Ed25519PrivateKey.generate()))
    assert coordinator.decide(sign())


def test_denial_cannot_be_flipped_to_approval():
    _, coordinator, _, sign = setup()
    forged = sign(False).model_dump()
    forged['approved'] = True
    with pytest.raises(ValueError, match="signature"):
        coordinator.decide(forged)
    assert coordinator.decide(sign(False)) is None


@pytest.mark.parametrize('field,value', [('resource','other'),('session_id','other'),('reviewer','attacker')])
def test_even_signed_modified_scope_rejected(field, value):
    _, coordinator, request, sign = setup()
    with pytest.raises(ValueError, match="modified"):
        coordinator.decide(sign(req=request.model_copy(update={field:value})))


def test_denial_expiry_and_restart():
    issuer, coordinator, request, sign = setup()
    assert coordinator.decide(sign(False)) is None
    with pytest.raises(ValueError): coordinator.decide(sign())
    _, coordinator, _, sign = setup()
    coordinator._clock = lambda:1120
    with pytest.raises(ValueError, match="expired"): coordinator.decide(sign())
    fresh = ConfirmationCoordinator('issuer', issuer, {}, clock=lambda:1001)
    with pytest.raises(ValueError): fresh.decide(sign())


def test_concurrent_confirmation_issues_once():
    _, coordinator, _, sign = setup()
    decision = sign()
    def attempt(_):
        try: return coordinator.decide(decision) is not None
        except ValueError: return False
    with ThreadPoolExecutor(max_workers=8) as pool:
        assert sum(pool.map(attempt, range(16))) == 1
