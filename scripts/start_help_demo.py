"""Start only the independent Reach help service on loopback.

Persistent local role files are provisioned once; never print or rotate them at
startup. No .env, device credential, payment key or reviewer file is loaded.
"""
import argparse
import json
import os
from pathlib import Path
import secrets
import socket

import uvicorn
from callgate.help_requests import HelpStore, HelpPrincipal
from callgate.help_transport import create_help_app


def provision(runtime):
    runtime.mkdir(mode=0o700,parents=True,exist_ok=True)
    runtime.chmod(0o700)
    credentials=runtime/'credentials.json'
    if not credentials.exists():
        rows=[{'token':secrets.token_urlsafe(36),'role':role,'actor_id':actor,'device_ids':['nano-01']}
              for role,actor in [('owner','owner-'+secrets.token_hex(8)),('contact','contact-'+secrets.token_hex(8)),('dashboard','display-'+secrets.token_hex(8))]]
        with credentials.open('x') as file:
            json.dump(rows,file)
    rows=json.loads(credentials.read_text())
    if len({row['token'] for row in rows})!=len(rows) or {row['role'] for row in rows}!={'owner','contact','dashboard'}:
        raise ValueError('invalid independent help roles')
    for row in rows:
        file=runtime/(row['role']+'.token')
        if not file.exists():
            with file.open('x') as output:
                output.write(row['token'])
    return {row['token']:HelpPrincipal(row['role'],row['actor_id'],tuple(row['device_ids'])) for row in rows}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inbox-db',type=Path,default=Path('.test-tmp/device-live/events.sqlite3'))
    parser.add_argument('--runtime-dir',type=Path,default=Path('.test-tmp/help-live'))
    parser.add_argument('--port',type=int,default=8783)
    args=parser.parse_args();os.umask(0o077)
    # Reserve the exact loopback port before provisioning; never fall back to a
    # payment/inbox port and never terminate an existing service.
    listener=socket.socket()
    listener.bind(('127.0.0.1',args.port));listener.listen(128)
    runtime=args.runtime_dir.resolve()
    try:
        credentials=provision(runtime)
        identities={p.role:p for p in credentials.values()}
        devices=set(identities['owner'].device_ids)&set(identities['contact'].device_ids)
        routes={device:{'owner':identities['owner'].actor_id,'contact':identities['contact'].actor_id} for device in devices}
        store=HelpStore(args.inbox_db,runtime/'help.sqlite3',routes)
        app=create_help_app(store,credentials)
        (runtime/'service.pid').write_text(str(os.getpid()))
        print('Reach help Dashboard: http://127.0.0.1:'+str(args.port)+'/',flush=True)
        print('Reach contact page: http://127.0.0.1:'+str(args.port)+'/contact',flush=True)
        print('Independent role access files saved locally; values not displayed.',flush=True)
        uvicorn.Server(uvicorn.Config(app,access_log=False,log_level='warning')).run(sockets=[listener])
    finally:
        listener.close()


if __name__=='__main__':main()
