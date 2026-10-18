"""Open one current local role on the operator's computer, without printing it.

This CLI is not a web endpoint. Local file access remains necessary for a role;
a participant HTTP capability cannot fetch the reviewer capability.
"""
import argparse
from pathlib import Path
import shutil
import subprocess
from urllib.parse import parse_qs, urlsplit


def role_entry(runtime, role, contact):
    name = 'participant-link.txt' if role in {'participant','operator'} else f'reviewer-{contact}-link.txt'
    if not contact or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-' for c in contact):
        raise ValueError('invalid contact identifier')
    path = (Path(runtime) / name).resolve()
    entry = path.read_text().strip()
    url = urlsplit(entry)
    if (url.scheme != 'http' or url.hostname != '127.0.0.1' or url.username or url.password
            or not url.port or url.path != '/' or not parse_qs(url.fragment).get('token')):
        raise ValueError('invalid local role entry')
    return path, entry if role != 'operator' else entry.replace('/#', '/fusion#', 1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('role', choices=['operator','participant','reviewer'])
    parser.add_argument('--contact', default='saved-family')
    parser.add_argument('--runtime-dir',type=Path,default=Path('.test-tmp/fusion-live'))
    args=parser.parse_args()
    try:
        path,entry=role_entry(args.runtime_dir,args.role,args.contact)
        if shutil.which('powershell.exe') and shutil.which('wslpath'):
            windows_path=subprocess.check_output(['wslpath','-w',str(path)],text=True).strip().replace("'","''")
            # Only a local file path is on the command line; the credential is not.
            command="$entry=(Get-Content -Raw -LiteralPath '"+windows_path+"').Trim(); "
            if args.role=='operator':
                command+="$entry=$entry.Replace('/#','/fusion#'); "
            command+="Start-Process -FilePath $entry"
            subprocess.run(['powershell.exe','-NoProfile','-Command',command],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        else:
            opener=shutil.which('wslview') or shutil.which('xdg-open') or shutil.which('open')
            if not opener:
                raise RuntimeError('No local browser opener is available.')
            subprocess.run([opener,entry],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        print('Opened the current local '+args.role+' view. Private access was not displayed.')
    except (OSError,ValueError,RuntimeError,subprocess.SubprocessError):
        parser.exit(1,'Could not open the local role. Run from your desktop terminal and check the private runtime files.\n')


if __name__=='__main__':
    main()
