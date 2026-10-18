from concurrent.futures import ThreadPoolExecutor
import sqlite3
import subprocess
import sys
import pytest
pytest.importorskip("cryptography")
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from callgate.verification import DemoVerificationGate, issue_for_demo
from callgate.replay_store import SQLiteReplayStore


def fixture(path, now=1001):
    key = Ed25519PrivateKey.generate()
    token = issue_for_demo(key, issuer="trusted", session_id="s", resource="r", now=1000)
    def gate():
        return DemoVerificationGate({"trusted":key.public_key()}, clock=lambda:now,
                                    replay_store=SQLiteReplayStore(path))
    return token, gate, dict(session_id="s", resource="r", human_confirmed=True, policy_allows=True)


def test_recreated_gate_rejects_consumed_token(tmp_path):
    token, gate, args = fixture(tmp_path / "replay.sqlite3")
    assert gate().execute(token, **args)["real_action_executed"] is False
    with pytest.raises(ValueError, match="consumed"):
        gate().execute(token, **args)


def test_consumption_survives_process_exit(tmp_path):
    path = tmp_path / "process.sqlite3"
    subprocess.run([sys.executable, "-c",
        "import sys; from callgate.replay_store import SQLiteReplayStore; "
        "SQLiteReplayStore(sys.argv[1]).consume('issuer','nonce',1000,1120,lambda:1001)",
        str(path)], check=True)
    with pytest.raises(ValueError, match="consumed"):
        SQLiteReplayStore(path).consume("issuer", "nonce", 1000, 1120, lambda:1002)


def test_independent_connections_race(tmp_path):
    token, gate, args = fixture(tmp_path / "race.sqlite3")
    gates = [gate() for _ in range(12)]
    def attempt(g):
        try: g.execute(token, **args); return True
        except ValueError: return False
    with ThreadPoolExecutor(max_workers=12) as pool:
        assert sum(pool.map(attempt, gates)) == 1


def test_expired_credential_does_not_consume_nonce(tmp_path):
    store = SQLiteReplayStore(tmp_path / "expiry.sqlite3")
    with pytest.raises(ValueError, match="valid"):
        store.consume("i", "n", 1000, 1120, lambda:1120)
    store.consume("i", "n", 1000, 1120, lambda:1001)
    with pytest.raises(ValueError, match="consumed"):
        store.consume("i", "n", 1000, 1120, lambda:1000)


def test_missing_schema_fails_closed(tmp_path):
    path = tmp_path / "broken.sqlite3"
    token, gate, args = fixture(path)
    g = gate()
    with sqlite3.connect(path) as db:
        db.execute("DROP TABLE consumed")
    with pytest.raises(ValueError, match="unavailable"):
        g.execute(token, **args)
