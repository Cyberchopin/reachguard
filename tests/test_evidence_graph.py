from fastapi.testclient import TestClient
from callgate.api import app
from callgate.engine import Conversation, EXTRACTOR_VERSION
from callgate.models import Transcript
from callgate.evidence_graph import evidence_graph


def segment(text, revision=0, final=True):
    return Transcript(segment_id="s", text=text, revision=revision,
                      final=final, start_ms=0, end_ms=1000)


def test_provisional_revision_and_detached_graph():
    c = Conversation()
    c.ingest(segment("Send money", final=False))
    provisional = evidence_graph(c)
    assert not any(n["type"] == "risk_category" for n in provisional["nodes"])
    c.ingest(segment("Send money", revision=1))
    g = evidence_graph(c)
    assert all(":s:0" not in n["id"] for n in g["nodes"])
    events = [n for n in g["nodes"] if n["type"] == "risk_event"]
    assert events[0]["extractor"] == EXTRACTOR_VERSION
    assert any(e["target"] == "risk:money" for e in g["edges"])
    g["nodes"].clear()
    assert evidence_graph(c)["nodes"]
    c.ingest(segment("Send Monday's agenda", revision=2))
    assert len(evidence_graph(c)["nodes"]) == 1
    assert evidence_graph(Conversation())["nodes"] == []


def test_latched_state_is_not_current_evidence():
    c = Conversation()
    c.ingest(segment("Share your password"))
    c.ingest(segment("Never share your password", revision=1))
    g = evidence_graph(c)
    assert g["policy_state"] == "BLOCKED"
    assert not g["edges"]
    assert not g["identity_verified"] and not g["protected_actions_allowed"]


def test_api_graph_contains_no_raw_transcript_and_no_dangling_edges():
    client = TestClient(app)
    body = {"segments": [segment("Send money now").model_dump()]}
    assert "evidence_graph" not in client.post('/v1/replay', json=body).json()
    result = client.post('/v1/replay?include_graph=true', json=body)
    assert result.status_code == 200
    g = result.json()["evidence_graph"]
    ids = {n["id"] for n in g["nodes"]}
    assert all(e["source"] in ids and e["target"] in ids for e in g["edges"])
    assert all("text" not in n for n in g["nodes"])
    assert len(ids) == len(g["nodes"])
