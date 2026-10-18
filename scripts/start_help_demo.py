"""Start only the independent Reach help service on loopback.

Persistent local role files are provisioned once; never print or rotate them at
startup. No .env, device credential, payment key or reviewer file is loaded.

With --contacts N (N > 1) the service rotates through N contacts in order
(contact.token is contact 1, then contact-2.token, ...), moving on after
--wait-seconds without acceptance. Existing role files are kept; only missing
contacts are added.
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
from callgate.reach_observability import configure_reach_sentry


def provision(runtime,contacts=1):
    runtime.mkdir(mode=0o700,parents=True,exist_ok=True)
    runtime.chmod(0o700)
    credentials=runtime/'credentials.json'
    if not credentials.exists():
        rows=[{'token':secrets.token_urlsafe(36),'role':role,'actor_id':actor,'device_ids':['nano-01']}
              for role,actor in [('owner','owner-'+secrets.token_hex(8)),('contact','contact-'+secrets.token_hex(8)),('dashboard','display-'+secrets.token_hex(8))]]
        with credentials.open('x') as file:
            json.dump(rows,file)
    rows=json.loads(credentials.read_text())
    missing=contacts-sum(row['role']=='contact' for row in rows)
    if missing>0:
        rows+=[{'token':secrets.token_urlsafe(36),'role':'contact','actor_id':'contact-'+secrets.token_hex(8),'device_ids':['nano-01']} for _ in range(missing)]
        replacement=runtime/'credentials.json.new'
        with replacement.open('x') as file:
            json.dump(rows,file)
        replacement.replace(credentials)
    if len({row['token'] for row in rows})!=len(rows) or {row['role'] for row in rows}!={'owner','contact','dashboard'}:
        raise ValueError('invalid independent help roles')
    seen=0
    for row in rows:
        name=row['role']
        if name=='contact':
            seen+=1
            name='contact' if seen==1 else f'contact-{seen}'
        file=runtime/(name+'.token')
        if not file.exists():
            with file.open('x') as output:
                output.write(row['token'])
    return {row['token']:HelpPrincipal(row['role'],row['actor_id'],tuple(row['device_ids'])) for row in rows}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inbox-db',type=Path,default=Path('.test-tmp/device-live/events.sqlite3'))
    parser.add_argument('--runtime-dir',type=Path,default=Path('.test-tmp/help-live'))
    parser.add_argument('--port',type=int,default=8783)
    parser.add_argument('--contacts',type=int,default=1,help='contacts to rotate through (1 = no rotation)')
    parser.add_argument('--wait-seconds',type=int,default=20,help='rotation wait per contact')
    args=parser.parse_args();os.umask(0o077)
    # Reserve the exact loopback port before provisioning; never fall back to a
    # payment/inbox port and never terminate an existing service.
    listener=socket.socket()
    listener.bind(('127.0.0.1',args.port));listener.listen(128)
    runtime=args.runtime_dir.resolve()
    try:
        credentials=provision(runtime,args.contacts)
        identities={p.role:p for p in credentials.values() if p.role!='contact'}
        contacts=[p for p in credentials.values() if p.role=='contact'][:max(args.contacts,1)]
        devices=set(identities['owner'].device_ids).intersection(*(c.device_ids for c in contacts))
        routes={device:{'owner':identities['owner'].actor_id,'contact':contacts[0].actor_id,
                        **({'contacts':[c.actor_id for c in contacts]} if len(contacts)>1 else {})} for device in devices}
        configure_reach_sentry()
        store=HelpStore(args.inbox_db,runtime/'help.sqlite3',routes,wait_seconds=args.wait_seconds)
        app=create_help_app(store,credentials)
        (runtime/'service.pid').write_text(str(os.getpid()))
        print('Reach help Dashboard: http://127.0.0.1:'+str(args.port)+'/',flush=True)
        print('Reach contact page: http://127.0.0.1:'+str(args.port)+'/contact',flush=True)
        if len(contacts)>1:
            print(f'Contact rotation: {len(contacts)} contacts, {args.wait_seconds} s each (contact.token, contact-2.token, ...)',flush=True)
        print('Independent role access files saved locally; values not displayed.',flush=True)
        uvicorn.Server(uvicorn.Config(app,access_log=False,log_level='warning')).run(sockets=[listener])
    finally:
        listener.close()


if __name__=='__main__':main()
