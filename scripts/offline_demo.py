"""Offline scenario assertions. No microphone, cloud calls or real actions.

Run from the repository root with verification dependencies installed:
python -m scripts.offline_demo
"""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from callgate.engine import Conversation
from callgate.models import Transcript
from callgate.evidence_graph import evidence_graph
from callgate.confirmation import ConfirmationCoordinator, ReviewerDecision, decision_bytes
from callgate.replay_store import SQLiteReplayStore
from callgate.verification import DemoVerificationGate


def run():
    conversation = Conversation()
    risk = conversation.ingest(Transcript(segment_id="demo", final=True,
        text="Send money. Do not tell anyone.", start_ms=0, end_ms=1000))
    assert risk["state"] == "COOLING_OFF"
    graph = evidence_graph(conversation)
    issuer, reviewer = Ed25519PrivateKey.generate(), Ed25519PrivateKey.generate()
    coordinator = ConfirmationCoordinator("demo-issuer", issuer,
        {"demo-reviewer":reviewer.public_key()})
    request = coordinator.create(session_id="demo-session", resource="demo-resource", reviewer="demo-reviewer")
    decision = ReviewerDecision(request=request, approved=True,
        signature=reviewer.sign(decision_bytes(request, True)).hex())
    credential = coordinator.decide(decision)
    with TemporaryDirectory(prefix="callgate-offline-") as directory:
        db = Path(directory) / "replay.sqlite3"
        def gate():
            return DemoVerificationGate({"demo-issuer":issuer.public_key()},
                replay_store=SQLiteReplayStore(db))
        args = dict(session_id="demo-session", resource="demo-resource", human_confirmed=True)
        try:
            gate().execute(credential, **args, policy_allows=False)
        except ValueError:
            blocked = True
        else:
            raise AssertionError("Policy denial bypassed")
        # Separate harness branch: explicitly simulate policy approval. This does
        # not clear the conversation state or establish a real verification.
        result = gate().execute(credential, **args, policy_allows=True)
        try:
            gate().execute(credential, **args, policy_allows=True)
        except ValueError as error:
            assert str(error) == "credential already consumed"
        else:
            raise AssertionError("Replay accepted")
    return dict(mode="offline-synthetic", cloud_calls=0, real_actions=0,
        risk_state=risk["state"], graph_nodes=len(graph["nodes"]), graph_edges=len(graph["edges"]),
        reviewer="generated_test_key_not_real_human", policy_denial_enforced=blocked,
        separate_policy_approval_branch=result["status"], replay_after_gate_recreation="rejected",
        original_conversation_state=conversation.state,
        note="Temporary replay database deleted; no real identity enrollment or policy unlock demonstrated.")


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
