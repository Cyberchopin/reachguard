"""Bounded, separate ngrok help endpoint; never reuse/pool the device endpoint.

ngrok loads its own private configuration. This launcher never reads its token.
If account/network startup fails, stop only this new agent and report codes.
"""
import argparse
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import time
from urllib.parse import urlsplit
from urllib.request import build_opener, ProxyHandler


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime-dir',type=Path,default=Path('.test-tmp/help-live'))
    parser.add_argument('--ngrok-config',type=Path,default=Path('.test-tmp/device-live/ngrok.yml'))
    parser.add_argument('--ngrok-binary',type=Path,default=Path('.test-tmp/device-live/ngrok'))
    parser.add_argument('--url',required=True,help='A separate HTTPS domain your account can bind; never the existing device domain')
    args=parser.parse_args();os.umask(0o077)
    runtime=args.runtime_dir.resolve();runtime.mkdir(mode=0o700,parents=True,exist_ok=True)
    opener=build_opener(ProxyHandler({}))
    def tunnels(port):
        with opener.open(f'http://127.0.0.1:{port}/api/tunnels',timeout=1) as response:
            return json.load(response).get('tunnels',[])
    protected=tunnels(4040)
    target=args.url
    url=urlsplit(target)
    if url.scheme!='https' or not url.netloc or url.username or url.password or url.path not in {'','/'}:
        parser.error('Supply a plain, separate HTTPS endpoint origin.')
    if any(urlsplit(t.get('public_url','')).netloc==url.netloc for t in protected):
        parser.error('Refusing to use the protected device endpoint domain.')
    with socket.socket() as check:
        check.bind(('127.0.0.1',4041))
    config=runtime/'ngrok-override.yml'
    config.write_text('version: 3\nagent:\n  web_addr: 127.0.0.1:4041\n  inspect_db_size: -1\n  remote_management: false\n  update_check: false\n')
    if not args.ngrok_config.is_file() or not args.ngrok_binary.is_file():
        parser.error('Local ngrok executable and separately configured account file required.')
    with (runtime/'ngrok.log').open('wb') as log:
        process=subprocess.Popen([str(args.ngrok_binary.resolve()),'http','http://127.0.0.1:8783',
            '--config',str(args.ngrok_config.resolve())+','+str(config),
            '--url',target,'--inspect=false','--log=stdout','--log-format=json'],
            stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True)
    (runtime/'ngrok.pid').write_text(str(process.pid))
    ready=False
    try:
        for _ in range(25):
            if process.poll() is not None:break
            try:
                for entry in tunnels(4041):
                    if entry.get('public_url','').rstrip('/')==target.rstrip('/'):
                        if entry.get('config',{}).get('addr')!='http://127.0.0.1:8783':
                            raise RuntimeError('Unexpected help origin')
                        assert [(t['public_url'],t['config']['addr']) for t in tunnels(4040)]==[(t['public_url'],t['config']['addr']) for t in protected]
                        (runtime/'base-url.txt').write_text(target)
                        (runtime/'tunnel-result.json').write_text(json.dumps({'available':True,'url':target,'upstream':'http://127.0.0.1:8783','device_tunnel_unchanged':True},indent=2))
                        ready=True
                        print('Help HTTPS:',target)
                        return 0
            except (OSError,ValueError):pass
            time.sleep(1)
    finally:
        if not ready and process.poll() is None:
            process.terminate();process.wait(timeout=5)
    codes=sorted(set(re.findall(r'ERR_NGROK_\d+',(runtime/'ngrok.log').read_text())))
    unchanged=[(t['public_url'],t['config']['addr']) for t in tunnels(4040)]==[(t['public_url'],t['config']['addr']) for t in protected]
    report={'available':False,'attempted_url':target,'error_codes':codes,'new_agent_stopped':True,'device_tunnel_unchanged':unchanged}
    (runtime/'tunnel-result.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report))
    return 1


if __name__=='__main__':raise SystemExit(main())
