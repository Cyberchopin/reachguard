"""SQLite replay ledger for gates on one host sharing the same local file.

No automatic deletion: consumed nonces remain consumed after clock rollback.
Database loss/restoration requires invalidating previously issued credentials.
"""
import sqlite3
from contextlib import closing
from pathlib import Path


class SQLiteReplayStore:
    def __init__(self, path):
        if str(path) == ":memory:":
            raise ValueError("persistent replay store requires a file")
        self.path = str(Path(path).resolve())
        with closing(self._connect()) as db, db:
            db.execute("CREATE TABLE IF NOT EXISTS consumed (issuer TEXT NOT NULL, nonce TEXT NOT NULL, PRIMARY KEY (issuer, nonce))")

    def _connect(self):
        db = sqlite3.connect(self.path, timeout=5)
        db.execute("PRAGMA synchronous=FULL")
        return db

    def consume(self, issuer, nonce, issued_at, expires_at, clock):
        try:
            with closing(self._connect()) as db, db:
                db.execute("BEGIN IMMEDIATE")
                # Check after obtaining the write lock; waiting may cross expiry.
                now = int(clock())
                if not issued_at <= now < expires_at:
                    raise ValueError("credential not currently valid")
                db.execute("INSERT INTO consumed (issuer, nonce) VALUES (?, ?)", (issuer, nonce))
        except sqlite3.IntegrityError:
            raise ValueError("credential already consumed") from None
        except sqlite3.Error:
            # Storage failure must never turn into successful authorization.
            raise ValueError("replay storage unavailable") from None
