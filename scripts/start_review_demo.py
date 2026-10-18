"""Start ephemeral loopback broker and reviewer processes. No persistent key file.

Run: python -m scripts.start_review_demo
Only the reviewer child generates/holds its private key. Startup URLs are local
role capabilities; keep the reviewer URL away from the participant browser.
"""
import argparse
import json
import multiprocessing as mp
import os
import secrets
import socket
import time
from pathlib import Path
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.error import HTTPError

import uvicorn
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from callgate.confirmation import ConfirmationCoordinator
from callgate.contacts import ContactDirectory, SavedContact
from callgate.review_transport import create_broker_app, create_reviewer_app
from callgate.verification import DemoVerificationGate
from callgate.workflow import DemoWorkflow


class NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _reviewer(public_pipe, broker_origin, reviewer_origin, reviewer_token, listener,
              reviewer_identity='local-reviewer'):
    key = Ed25519PrivateKey.generate()
    public_pipe.send_bytes(key.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw))
    public_pipe.close()
    opener = build_opener(NoRedirects)

    def call(path, body=None):
        request = Request(broker_origin + path,
            data=None if body is None else json.dumps(body).encode(),
            headers={'Authorization': 'Bearer ' + reviewer_token, 'Content-Type': 'application/json'})
        try:
            with opener.open(request, timeout=5) as response:
                return json.load(response)
        except HTTPError as error:
            if error.code == 409:
                raise ValueError('confirmation no longer valid') from None
            raise

    app = create_reviewer_app(key, reviewer_token,
        lambda: call('/api/review/pending'),
        lambda submission: call('/api/review/decision', submission.model_dump()), origin=reviewer_origin,
        expected_reviewer=reviewer_identity)
    uvicorn.Server(uvicorn.Config(app, access_log=False, log_level='warning')).run(sockets=[listener])


def _broker(public_bytes, participant_token, reviewer_token, origin, listener, contact_identity,
            extra_contacts=(), device_inbox=None, fusion_state=None):
    issuer = Ed25519PrivateKey.generate()
    rows = [dict(identity=contact_identity, reviewer='local-reviewer',
                 public_bytes=public_bytes, token=reviewer_token), *extra_contacts]
    directory = ContactDirectory([SavedContact(identity=row['identity'], reviewer=row['reviewer'],
        credential_origin=row['reviewer'] + '-process') for row in rows])
    coordinator = ConfirmationCoordinator('local-demo', issuer,
        {row['reviewer']:Ed25519PublicKey.from_public_bytes(row['public_bytes']) for row in rows},
        contacts=directory, initiator_origin='local-participant-session')
    workflow = DemoWorkflow(coordinator, DemoVerificationGate({'local-demo': issuer.public_key()}),
                            None)
    app = create_broker_app(workflow, participant_token,
        {row['reviewer']:row['token'] for row in rows}, origin=origin,
        metrics_database=Path(__file__).resolve().parents[1] / 'callgate-metrics.sqlite3',
        device_inbox=device_inbox, fusion_state=fusion_state)
    uvicorn.Server(uvicorn.Config(app, access_log=False, log_level='warning')).run(sockets=[listener])


def _bind(port):
    sock = socket.socket()
    try:
        sock.bind(('127.0.0.1', port))
        sock.listen(128)
        return sock
    except BaseException:
        sock.close()
        raise


def _bind_with_fallback(preferred_port):
    for port in [preferred_port, 0]:
        try:
            return _bind(port)
        except OSError as error:
            if port == preferred_port and error.errno in {48, 98, 10048}:
                continue
            raise


def _contact_ids(values):
    identities = ['saved-family'] if values is None else list(values)
    if not 1 <= len(identities) <= 4 or len(set(identities)) != len(identities):
        raise ValueError('supply distinct saved identities within the local demo capacity')
    for identity in identities:
        SavedContact(identity=identity, reviewer='placeholder', credential_origin='placeholder')
    return identities


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--participant-port', type=int, default=8766)
    parser.add_argument('--reviewer-port', type=int, default=8767)
    parser.add_argument('--contact-identity', action='append',
        help='Repeat for separate synthetic saved contacts; default saved-family')
    parser.add_argument('--device-events-db', type=Path,
        help='Opt in to local fusion page; read-only existing device inbox database')
    parser.add_argument('--fusion-runtime-dir', type=Path,
        help='Private local runtime directory for fusion state and role entry files')
    args = parser.parse_args()
    if bool(args.device_events_db) != bool(args.fusion_runtime_dir):
        parser.error('device-events-db and fusion-runtime-dir must be supplied together')
    runtime = args.fusion_runtime_dir
    if runtime is not None:
        runtime = runtime.resolve()
        runtime.mkdir(mode=0o700, parents=True, exist_ok=True)
        runtime.chmod(0o700)
        if not args.device_events_db.is_file():
            parser.error('existing device inbox database required')
        os.umask(0o077)
    try:
        identities = _contact_ids(args.contact_identity)
    except ValueError as error:
        parser.error(str(error))
    env_path = Path(__file__).resolve().parents[1] / '.env'
    if runtime is None and env_path.exists() and not os.environ.get('ASSEMBLYAI_API_KEY'):
        for line in env_path.read_text(encoding='utf-8-sig').splitlines():
            if line.startswith('ASSEMBLYAI_API_KEY='):
                os.environ['ASSEMBLYAI_API_KEY'] = line.split('=', 1)[1].strip()
    sockets, children = [], []
    try:
        sockets.append(_bind_with_fallback(args.participant_port))
        broker_origin = 'http://127.0.0.1:' + str(sockets[0].getsockname()[1])
        participant_token = secrets.token_urlsafe(32)
        context = mp.get_context('spawn')
        rows = []
        for index, identity in enumerate(identities):
            sockets.append(_bind_with_fallback(args.reviewer_port if index == 0 else 0))
            reviewer_origin = 'http://127.0.0.1:' + str(sockets[-1].getsockname()[1])
            reviewer_name = 'local-reviewer' if index == 0 else f'local-reviewer-{index}'
            reviewer_token = secrets.token_urlsafe(32)
            receive, send = context.Pipe(duplex=False)
            try:
                reviewer = context.Process(target=_reviewer,
                    args=(send, broker_origin, reviewer_origin, reviewer_token, sockets[-1], reviewer_name))
                reviewer.start()
                children.append(reviewer)
                send.close()
                if not receive.poll(15):
                    raise RuntimeError('reviewer startup failed')
                rows.append(dict(identity=identity, reviewer=reviewer_name, token=reviewer_token,
                                 public_bytes=receive.recv_bytes(), origin=reviewer_origin))
            finally:
                receive.close()
                send.close()
        broker = context.Process(target=_broker,
            args=(rows[0]['public_bytes'], participant_token, rows[0]['token'], broker_origin, sockets[0],
                  rows[0]['identity'], rows[1:],
                  None if runtime is None else args.device_events_db.resolve(),
                  None if runtime is None else runtime / 'fusion.sqlite3'))
        broker.start()
        children.append(broker)
        if runtime is None:
            # Existing launcher behavior; capabilities remain in user's own terminal.
            print('Participant: ' + broker_origin + '/#token=' + participant_token, flush=True)
            for row in rows:
                print('Reviewer [' + row['identity'] + '] (keep separate): ' + row['origin'] +
                      '/#token=' + row['token'], flush=True)
        else:
            (runtime / 'operator.token').write_text(participant_token)
            (runtime / 'participant-link.txt').write_text(broker_origin + '/#token=' + participant_token)
            for row in rows:
                (runtime / ('reviewer-' + row['identity'] + '-link.txt')).write_text(
                    row['origin'] + '/#token=' + row['token'])
            print('Local fusion operator: ' + broker_origin + '/fusion', flush=True)
            print('Private role entry files saved locally; credentials not printed.', flush=True)
        print('Local demo only. Keys expire on restart. Ctrl+C stops all processes.', flush=True)
        print('Synthetic startup enrollment; one operator may still control all roles.', flush=True)
        while all(child.is_alive() for child in children):
            time.sleep(0.25)
        raise RuntimeError('one service stopped; restart both services')
    except KeyboardInterrupt:
        return 0
    finally:
        for child in children:
            if child.is_alive():
                child.terminate()
            child.join(timeout=5)
        for sock in sockets:
            sock.close()


if __name__ == '__main__':
    raise SystemExit(main())
