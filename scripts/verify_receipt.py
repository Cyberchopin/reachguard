"""Verify a receipt using an independently retained expected key and session."""
import argparse
import json
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from callgate.receipt import verify_receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('path', type=Path)
    parser.add_argument('--public-key', required=True, help='Expected Ed25519 public key hex')
    parser.add_argument('--session', required=True, help='Expected session ID')
    args = parser.parse_args()
    try:
        if args.path.stat().st_size > 65536:
            raise ValueError('receipt too large')
        bundle = json.loads(args.path.read_text(encoding='utf-8'))
        key = Ed25519PublicKey.from_public_bytes(bytes.fromhex(args.public_key))
        verify_receipt(bundle['receipt'], key, session_id=args.session)
    except (OSError, ValueError, KeyError, TypeError):
        print('INVALID: receipt, expected key or expected session did not validate.')
        return 1
    print('VALID SIGNATURE AND SESSION: does not establish identity, judgment accuracy or action authorization.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
