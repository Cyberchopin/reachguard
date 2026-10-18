"""Local simulated authorization gate; issuer enrollment is trusted configuration.

Uses pyca Ed25519. Supply a shared SQLiteReplayStore for durable replay checks.
The default in-memory mode is for disposable single-instance tests only.
No real payment, identity enrollment, or user-confirmation transport is provided.
"""
import json
import secrets
import threading
import time
from typing import Literal
from pydantic import Field, model_validator
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from .models import StrictModel


class VerificationClaim(StrictModel):
    version: Literal["callgate-verification-v1"] = "callgate-verification-v1"
    issuer: str = Field(min_length=1, max_length=80)
    session_id: str = Field(min_length=1, max_length=80)
    action: Literal["simulate_protected_action"] = "simulate_protected_action"
    resource: str = Field(min_length=1, max_length=120)
    issued_at: int = Field(ge=0)
    expires_at: int = Field(ge=0)
    nonce: str = Field(pattern=r"^[a-f0-9]{64}$")

    @model_validator(mode="after")
    def lifetime(self):
        if not 0 < self.expires_at - self.issued_at <= 300:
            raise ValueError("credential lifetime must be within 300 seconds")
        return self


class SignedVerification(StrictModel):
    claim: VerificationClaim
    signature: str = Field(pattern=r"^[a-f0-9]{128}$")


def signing_bytes(claim):
    return json.dumps(claim.model_dump(), sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("ascii")


def issue_for_demo(key: Ed25519PrivateKey, *, issuer, session_id, resource, now=None):
    """Trusted test issuer only. Calling this function does not verify a person."""
    now = int(time.time()) if now is None else now
    claim = VerificationClaim(issuer=issuer, session_id=session_id, resource=resource,
                              issued_at=now, expires_at=now+120, nonce=secrets.token_hex(32))
    return SignedVerification(claim=claim, signature=key.sign(signing_bytes(claim)).hex())


class DemoVerificationGate:
    def __init__(self, trusted_issuers, *, clock=time.time, replay_store=None):
        self._issuers = dict(trusted_issuers)
        self._clock = clock
        self._replay_store = replay_store
        self._consumed = {}
        self._lock = threading.Lock()

    def execute(self, credential, *, session_id, resource, human_confirmed=False,
                policy_allows=False):
        """Confirmation/policy inputs must come from trusted orchestration, not caller JSON."""
        credential = SignedVerification.model_validate(credential)
        c = credential.claim
        key = self._issuers.get(c.issuer)
        if key is None:
            raise ValueError("unknown issuer")
        try:
            key.verify(bytes.fromhex(credential.signature), signing_bytes(c))
        except InvalidSignature:
            raise ValueError("invalid signature") from None
        if c.session_id != session_id or c.resource != resource:
            raise ValueError("scope mismatch")
        if human_confirmed is not True or policy_allows is not True:
            raise ValueError("confirmation and policy approval required")
        if self._replay_store is not None:
            self._replay_store.consume(c.issuer, c.nonce, c.issued_at, c.expires_at, self._clock)
            return {"status":"simulated_action_completed", "session_id":session_id,
                    "resource":resource, "real_action_executed":False}
        with self._lock:
            now = int(self._clock())
            if not c.issued_at <= now < c.expires_at:
                raise ValueError("credential not currently valid")
            self._consumed = {k:v for k,v in self._consumed.items() if v > now}
            nonce_key = (c.issuer, c.nonce)
            if nonce_key in self._consumed:
                raise ValueError("credential already consumed")
            if len(self._consumed) >= 10000:
                raise ValueError("gate capacity reached")
            self._consumed[nonce_key] = c.expires_at
            return {"status":"simulated_action_completed", "session_id":session_id,
                    "resource":resource, "real_action_executed":False}
