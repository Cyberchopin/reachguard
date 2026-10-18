"""Exercise authenticated artifacts against the actual broker workflow."""
import json
import subprocess
import sys
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from callgate.receipt import verify_receipt
from test_review_transport import demo, request_action, bearer, PARTICIPANT_TOKEN, REVIEWER_TOKEN


def test_graph_receipt_export_and_offline_verification(demo, tmp_path):
    request_action(demo)
    headers = bearer(PARTICIPANT_TOKEN)
    evidence = demo.broker.get('/api/evidence', headers=headers).json()
    assert evidence['score'] == 50
    assert {r['kind'] for r in evidence['contributions']} == {'money', 'urgency'}
    assert 'Send money' not in json.dumps(evidence)
    bundle = demo.broker.post('/api/receipt', json={}, headers=headers).json()
    expected_key = demo.broker.get('/api/receipt-key', headers=headers).json()['public_key_hex']
    expected_session = bundle['receipt']['payload']['session_id']
    assert verify_receipt(bundle['receipt'], Ed25519PublicKey.from_public_bytes(bytes.fromhex(expected_key)),
                          session_id=expected_session).decision == 'CHALLENGED'
    assert 'Send money' not in json.dumps(bundle)
    path = tmp_path / 'receipt.json'
    path.write_text(json.dumps(bundle), encoding='utf-8')
    command = [sys.executable, '-m', 'scripts.verify_receipt', str(path),
               '--public-key', expected_key, '--session', expected_session]
    assert subprocess.run(command, capture_output=True).returncode == 0
    bundle['receipt']['payload']['score'] = 0
    path.write_text(json.dumps(bundle), encoding='utf-8')
    assert subprocess.run(command, capture_output=True).returncode == 1
    demo.workflow.reset_session()
    assert demo.broker.post('/api/receipt', json={}, headers=headers).status_code == 409
    assert demo.broker.get('/api/evidence', headers=headers).json()['graph']['nodes'] == []


@pytest.mark.parametrize('token', [None, REVIEWER_TOKEN])
@pytest.mark.parametrize('route', ['/api/evidence', '/api/receipt-key', '/api/metrics/export'])
def test_artifacts_require_participant(demo, token, route):
    assert demo.broker.get(route, headers={} if token is None else bearer(token)).status_code == 401


def test_receipt_does_not_accept_reviewer_capability(demo):
    assert demo.broker.post('/api/receipt', json={}, headers=bearer(REVIEWER_TOKEN)).status_code == 401


def test_export_is_versioned_download_without_credentials(demo):
    response = demo.broker.get('/api/metrics/export', headers=bearer(PARTICIPANT_TOKEN))
    assert response.headers['cache-control'] == 'no-store'
    assert 'attachment' in response.headers['content-disposition']
    result = response.json()
    assert result['schema_version'] == 'callgate-live-metrics-v2'
    assert result['samples'] == []
    assert PARTICIPANT_TOKEN not in response.text and REVIEWER_TOKEN not in response.text
