"""Signed minimal decision receipt. This records a decision; it does not prove it was correct."""
import hashlib
import json
import secrets
import time
from typing import Literal
from pydantic import Field
from cryptography.exceptions import InvalidSignature
from .models import StrictModel


class ReceiptPayload(StrictModel):
    version: Literal["callgate-receipt-v1"] = "callgate-receipt-v1"
    receipt_id: str = Field(pattern=r"^[a-f0-9]{64}$")
    session_id: str = Field(min_length=1, max_length=80)
    issued_at: int = Field(ge=0)
    policy_version: str = Field(min_length=1, max_length=40)
    extractor: str = Field(min_length=1, max_length=40)
    decision: Literal["UNVERIFIED", "CHALLENGED", "COOLING_OFF", "BLOCKED"]
    score: int = Field(ge=0, le=100)
    score_kind: Literal["heuristic_not_probability"] = "heuristic_not_probability"
    evidence_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    protected_actions_allowed: Literal[False] = False


class SignedReceipt(StrictModel):
    payload: ReceiptPayload
    signature: str = Field(pattern=r"^[a-f0-9]{128}$")


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("ascii")


def current_evidence(conversation):
    """Stable metadata only; no transcript text, confidence, or event ID."""
    rows = []
    for sid in sorted(conversation.events):
        segment = conversation.segments[sid]
        if not segment.final:
            continue
        for event in conversation.events[sid]:
            rows.append({"segment_id":sid, "revision":segment.revision,
                         "kind":event.kind, "start":event.start, "end":event.end,
                         "extractor":event.extractor})
    return rows


def issue_receipt(conversation, signing_key, *, session_id, now=None):
    snapshot = conversation.snapshot()
    payload = ReceiptPayload(receipt_id=secrets.token_hex(32), session_id=session_id,
        issued_at=int(time.time()) if now is None else now,
        policy_version=snapshot["policy_version"], extractor=snapshot["extractor"],
        decision=snapshot["state"], score=snapshot["score"],
        evidence_sha256=hashlib.sha256(canonical(current_evidence(conversation))).hexdigest())
    return SignedReceipt(payload=payload, signature=signing_key.sign(canonical(payload.model_dump())).hex())


def verify_receipt(receipt, public_key, *, session_id):
    receipt = SignedReceipt.model_validate(receipt)
    try:
        public_key.verify(bytes.fromhex(receipt.signature), canonical(receipt.payload.model_dump()))
    except InvalidSignature:
        raise ValueError("invalid receipt signature") from None
    if receipt.payload.session_id != session_id:
        raise ValueError("receipt session mismatch")
    return receipt.payload
