from concurrent.futures import ThreadPoolExecutor
import pytest
pytest.importorskip("cryptography")
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from callgate.verification import DemoVerificationGate, issue_for_demo


def setup():
    key = Ed25519PrivateKey.generate()
    token = issue_for_demo(key, issuer="registered", session_id="session-a", resource="demo-a", now=1000)
    gate = DemoVerificationGate({"registered":key.public_key()}, clock=lambda:1001)
    args = dict(session_id="session-a", resource="demo-a", human_confirmed=True, policy_allows=True)
    return token, gate, args


def test_success_then_replay_rejected():
    token, gate, args = setup()
    assert gate.execute(token, **args)["real_action_executed"] is False
    with pytest.raises(ValueError, match="consumed"): gate.execute(token, **args)


@pytest.mark.parametrize("field,value", [("resource","demo-b"),("session_id","session-b"),
    ("human_confirmed",False),("policy_allows",False),("human_confirmed","true")])
def test_scope_policy_and_confirmation(field, value):
    token, gate, args = setup()
    with pytest.raises(ValueError): gate.execute(token, **dict(args, **{field:value}))
    assert gate.execute(token, **args)["status"] == "simulated_action_completed"


@pytest.mark.parametrize("field,value", [("resource","demo-b"),("expires_at",1121),
    ("issuer","attacker"),("action","transfer_money"),("verified",True)])
def test_tampering_and_forged_fields(field, value):
    token, gate, args = setup()
    forged = token.model_dump()
    forged["claim"][field] = value
    with pytest.raises(ValueError): gate.execute(forged, **args)


@pytest.mark.parametrize("now", [999,1120,1200])
def test_time_boundaries(now):
    token, gate, args = setup()
    gate._clock = lambda:now
    with pytest.raises(ValueError): gate.execute(token, **args)


def test_attacker_key_and_atomic_concurrent_replay():
    token, gate, args = setup()
    forged = issue_for_demo(Ed25519PrivateKey.generate(), issuer="registered",
                           session_id="session-a", resource="demo-a", now=1000)
    with pytest.raises(ValueError, match="signature"): gate.execute(forged, **args)
    def attempt(_):
        try: return gate.execute(token, **args)["status"]
        except ValueError: return "rejected"
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(attempt, range(16)))
    assert results.count("simulated_action_completed") == 1
