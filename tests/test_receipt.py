import pytest
pytest.importorskip("cryptography")
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from callgate.engine import Conversation
from callgate.models import Transcript
from callgate.receipt import current_evidence, issue_receipt, verify_receipt


def conversation(text="Send money. Do not tell anyone."):
    c = Conversation()
    c.ingest(Transcript(segment_id="s", text=text, final=True, start_ms=0, end_ms=1000))
    return c


def test_signed_minimal_receipt():
    key, c = Ed25519PrivateKey.generate(), conversation()
    receipt = issue_receipt(c,key,session_id="session",now=1000)
    payload = verify_receipt(receipt,key.public_key(),session_id="session")
    assert payload.decision == "COOLING_OFF" and payload.score == 55
    assert payload.protected_actions_allowed is False
    raw = str(receipt.model_dump())
    assert "Send money" not in raw and "Do not tell" not in raw


@pytest.mark.parametrize("field,value", [("score",0),("decision","UNVERIFIED"),
    ("policy_version","attacker"),("evidence_sha256","0"*64),
    ("protected_actions_allowed",True)])
def test_tampering_rejected(field,value):
    key, c = Ed25519PrivateKey.generate(), conversation()
    forged = issue_receipt(c,key,session_id="session",now=1000).model_dump()
    forged["payload"][field] = value
    with pytest.raises(ValueError):
        verify_receipt(forged,key.public_key(),session_id="session")


def test_wrong_key_session_and_current_revision():
    key, c = Ed25519PrivateKey.generate(), conversation()
    old = current_evidence(c)
    c.ingest(Transcript(segment_id="s",revision=1,text="Hello",final=True,start_ms=0,end_ms=1000))
    assert old and current_evidence(c) == []
    receipt = issue_receipt(c,key,session_id="session",now=1000)
    with pytest.raises(ValueError,match="signature"):
        verify_receipt(receipt,Ed25519PrivateKey.generate().public_key(),session_id="session")
    with pytest.raises(ValueError,match="session"):
        verify_receipt(receipt,key.public_key(),session_id="other")
