"""Loopback integration: real HTTP and two spawned processes, no external calls."""
import json
import multiprocessing as mp
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import pytest
pytest.importorskip('cryptography')
from scripts.start_review_demo import _bind, _broker, _reviewer


def call(origin, path, token, body=None):
    request = Request(origin + path, data=None if body is None else json.dumps(body).encode(),
        headers={'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json'})
    with urlopen(request, timeout=1) as response:
        return json.load(response)


def wait_ready(origin, path, token, children):
    until = time.monotonic() + 10
    while True:
        assert all(child.is_alive() for child in children)
        try:
            return call(origin, path, token)
        except (URLError, TimeoutError):
            if time.monotonic() >= until:
                raise
            time.sleep(0.05)


def test_two_process_approval_then_unavailable_reviewer():
    context = mp.get_context('spawn')
    participant_token, reviewer_token = 'process-participant-test', 'process-reviewer-test'
    broker_socket, reviewer_socket = _bind(0), _bind(0)
    broker_origin = 'http://127.0.0.1:' + str(broker_socket.getsockname()[1])
    reviewer_origin = 'http://127.0.0.1:' + str(reviewer_socket.getsockname()[1])
    receive, send = context.Pipe(duplex=False)
    children = []
    try:
        reviewer = context.Process(target=_reviewer,
            args=(send, broker_origin, reviewer_origin, reviewer_token, reviewer_socket))
        reviewer.start()
        children.append(reviewer)
        send.close()
        assert receive.poll(10), 'reviewer failed to provide public key'
        broker = context.Process(target=_broker,
            args=(receive.recv_bytes(), participant_token, reviewer_token, broker_origin, broker_socket,
                  'saved-family'))
        broker.start()
        children.append(broker)
        # Child owns its duplicated listening socket; close parent duplicates.
        broker_socket.close()
        reviewer_socket.close()

        wait_ready(broker_origin, '/api/status', participant_token, children)
        wait_ready(reviewer_origin, '/api/pending', reviewer_token, children)
        consent = call(broker_origin, '/api/processing-consent', participant_token,
                       {'granted': True})
        assert consent['processing_allowed'] is True
        risk = call(broker_origin, '/api/transcript', participant_token, dict(segment_id='s1',
            text='Move your savings into the secure holding wallet.', start_ms=0, end_ms=1000, final=True))
        assert risk['state'] == 'CHALLENGED'
        assert call(broker_origin, '/api/contacts', participant_token)['identities'] == ['saved-family']
        operation = {'destination': '测试-wallet', 'amount_cents': 280000}
        with pytest.raises(HTTPError) as missing_identity:
            call(broker_origin, '/api/request', participant_token, operation)
        assert missing_identity.value.code == 409
        operation['claimed_identity'] = 'saved-family'
        bundle = call(broker_origin, '/api/request', participant_token, operation)
        assert bundle['request']['claimed_identity'] == 'saved-family'
        expected_pending = {k: bundle[k] for k in ('request', 'operation')}
        assert call(reviewer_origin, '/api/pending', reviewer_token) == expected_pending
        approval = {'request_id': bundle['request']['request_id'], 'approved': True,
                    'challenge_response': bundle['out_of_band_challenge']}
        result = call(reviewer_origin, '/api/decide', reviewer_token, approval)
        assert result['status'] == 'simulated_action_completed'
        assert result['real_action_executed'] is False
        assert call(broker_origin, '/api/status', participant_token)['outcome'] == result
        with pytest.raises(HTTPError) as error:
            call(reviewer_origin, '/api/decide', reviewer_token, approval)
        assert error.value.code == 409
        call(broker_origin, '/api/request', participant_token, operation)
        reviewer.terminate()
        reviewer.join(timeout=5)
        with pytest.raises((URLError, TimeoutError)):
            call(reviewer_origin, '/api/pending', reviewer_token)
        status = call(broker_origin, '/api/status', participant_token)
        assert status['pending'] is True and status['outcome'] is None
    finally:
        for child in children:
            if child.is_alive():
                child.terminate()
            child.join(timeout=5)
        receive.close()
        send.close()
        broker_socket.close()
        reviewer_socket.close()

def test_three_process_routing_switch_and_cross_contact_isolation():
    context = mp.get_context('spawn')
    sockets = [_bind(0) for _ in range(3)]
    origins = ['http://127.0.0.1:' + str(s.getsockname()[1]) for s in sockets]
    broker_origin = origins[0]
    children, rows = [], []
    participant_token = 'multi-process-participant-test'
    try:
        for index, identity in enumerate(['saved-family', 'saved-bank']):
            receive, send = context.Pipe(duplex=False)
            name = 'local-reviewer' if index == 0 else 'local-reviewer-1'
            token = 'multi-process-reviewer-test-' + str(index)
            child = context.Process(target=_reviewer, args=(send, broker_origin,
                origins[index+1], token, sockets[index+1], name))
            try:
                child.start()
                children.append(child)
                send.close()
                assert receive.poll(10), 'reviewer failed to provide public key'
                rows.append(dict(identity=identity, reviewer=name, token=token,
                                 public_bytes=receive.recv_bytes()))
            finally:
                receive.close()
                send.close()
        broker = context.Process(target=_broker, args=(rows[0]['public_bytes'], participant_token,
            rows[0]['token'], broker_origin, sockets[0], rows[0]['identity'], rows[1:]))
        broker.start()
        children.append(broker)
        for sock in sockets:
            sock.close()
        wait_ready(broker_origin, '/api/status', participant_token, children)
        for index, row in enumerate(rows):
            wait_ready(origins[index+1], '/api/pending', row['token'], children)
        assert call(broker_origin, '/api/contacts', participant_token)['identities'] == ['saved-bank','saved-family']
        call(broker_origin, '/api/processing-consent', participant_token, {'granted':True})
        call(broker_origin, '/api/transcript', participant_token, dict(segment_id='s',
            text='Send money.', start_ms=0, end_ms=1, final=True))
        operation = dict(destination='fictional-wallet', amount_cents=100, claimed_identity='saved-family')
        old = call(broker_origin, '/api/request', participant_token, operation)
        assert call(origins[1], '/api/pending', rows[0]['token'])['request']['claimed_identity'] == 'saved-family'
        assert call(origins[2], '/api/pending', rows[1]['token']) is None
        operation['claimed_identity'] = 'saved-bank'
        new = call(broker_origin, '/api/request', participant_token, operation)
        assert call(origins[1], '/api/pending', rows[0]['token']) is None
        assert call(origins[2], '/api/pending', rows[1]['token'])['request']['claimed_identity'] == 'saved-bank'
        approval = dict(request_id=new['request']['request_id'], approved=True,
                        challenge_response=new['out_of_band_challenge'])
        with pytest.raises(HTTPError) as wrong_channel:
            call(origins[1], '/api/decide', rows[0]['token'], approval)
        assert wrong_channel.value.code == 409
        with pytest.raises(HTTPError) as wrong_entry:
            call(origins[2], '/api/pending', rows[0]['token'])
        assert wrong_entry.value.code == 401
        result = call(origins[2], '/api/decide', rows[1]['token'], approval)
        assert result['status'] == 'simulated_action_completed'
        assert result['real_action_executed'] is False
        with pytest.raises(HTTPError) as replay:
            call(origins[2], '/api/decide', rows[1]['token'], approval)
        assert replay.value.code == 409
    finally:
        for child in children:
            if child.is_alive():
                child.terminate()
            child.join(timeout=5)
        for sock in sockets:
            sock.close()
