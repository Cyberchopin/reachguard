"""Bounded demo measurements, optionally durable; no content or identifiers."""
import math
import threading
import sqlite3
import json
from contextlib import closing
from collections import deque


def percentile(values, fraction):
    if not values:
        return None
    ordered = sorted(values)
    return ordered[math.ceil(fraction * len(ordered)) - 1]


class LiveMetrics:
    def __init__(self, capacity=100, *, database=None):
        if type(capacity) is not int or not 1 <= capacity <= 10_000:
            raise ValueError('invalid metrics capacity')
        self._rows = deque(maxlen=capacity)
        self._lock = threading.Lock()
        self._total = 0
        self._database = database
        if database is not None:
            with closing(sqlite3.connect(database)) as db, db:
                db.execute('CREATE TABLE IF NOT EXISTS metrics (id INTEGER PRIMARY KEY AUTOINCREMENT, value TEXT NOT NULL)')
                db.execute('DELETE FROM metrics WHERE id NOT IN (SELECT id FROM metrics ORDER BY id DESC LIMIT ?)', (capacity,))
                self._rows.extend(json.loads(r[0]) for r in db.execute('SELECT value FROM metrics ORDER BY id'))
                row = db.execute("SELECT seq FROM sqlite_sequence WHERE name='metrics'").fetchone()
                self._total = row[0] if row else 0

    def record(self, *, audio_ms, first_alert_proxy_ms, risk_engine_ms,
               completed=None, outcome=None, provider_connect_ms=None, provider_first_transcript_ms=None):
        if outcome is None:
            if type(completed) is not bool:
                raise ValueError('explicit outcome required')
            outcome = 'completed' if completed else 'failed'
        if outcome not in {'completed', 'failed', 'cancelled', 'disconnected'}:
            raise ValueError('invalid outcome')
        def number(value, optional=False):
            if value is None and optional:
                return None
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError('measurement must be numeric')
            if not math.isfinite(value) or value < 0:
                raise ValueError('measurement must be finite and nonnegative')
            return float(value)
        row = {
            'outcome': outcome,
            'audio_ms': number(audio_ms),
            'first_alert_proxy_ms': number(first_alert_proxy_ms, True),
            'risk_engine_ms': number(risk_engine_ms, True),
            'provider_connect_ms': number(provider_connect_ms, True),
            'provider_first_transcript_ms': number(provider_first_transcript_ms, True),
        }
        with self._lock:
            if self._database is not None:
                # Commit before acknowledging the measurement. No content or credentials.
                with closing(sqlite3.connect(self._database)) as db, db:
                    db.execute('INSERT INTO metrics(value) VALUES (?)', (json.dumps(row),))
                    db.execute('DELETE FROM metrics WHERE id NOT IN (SELECT id FROM metrics ORDER BY id DESC LIMIT ?)', (self._rows.maxlen,))
            self._rows.append(row)
            self._total += 1

    def summary(self):
        return self.export()['summary']

    def export(self):
        with self._lock:
            rows = [dict(row) for row in self._rows]
            total = self._total
        completed = sum(row['outcome'] == 'completed' for row in rows)
        failed = sum(row['outcome'] == 'failed' for row in rows)
        alerts = [row['first_alert_proxy_ms'] for row in rows
                  if row['outcome'] == 'completed' and row['first_alert_proxy_ms'] is not None]
        engines = [row['risk_engine_ms'] for row in rows
                   if row['risk_engine_ms'] is not None]
        summary = {
            'sessions': len(rows),
            'completed': completed,
            'failed': failed,
            'cancelled': sum(row['outcome'] == 'cancelled' for row in rows),
            'disconnected': sum(row['outcome'] == 'disconnected' for row in rows),
            'failure_denominator': completed + failed,
            'failure_rate': None if not completed + failed else failed / (completed + failed),
            'total_recorded': total,
            'evicted': total - len(rows),
            'alert_samples': len(alerts),
            'alert_proxy_p50_ms': percentile(alerts, .50),
            'alert_proxy_p95_ms': percentile(alerts, .95),
            'risk_engine_p50_ms': percentile(engines, .50),
            'risk_engine_p95_ms': percentile(engines, .95),
            'scope': ('persistent_bounded_no_content' if self._database is not None
                      else 'current_process_bounded_no_content'),
        }
        return {'schema_version': 'callgate-live-metrics-v2', 'summary': summary, 'samples': rows,
                'definitions': {
                    'failure_rate': 'failed / (completed + failed); cancellations and disconnects excluded',
                    'alert_proxy': 'first emitted final risk transition; completed streams with valid timestamps only',
                    'risk_engine': 'maximum ingest duration per stream; percentiles are over these maxima',
                    'provider_connect_ms': 'WebSocket connection setup elapsed, including network/TLS/upgrade',
                    'provider_first_transcript_ms': 'first PCM send start to first nonempty normalized transcript; includes supplied audio duration, buffering and endpointing; NOT network RTT or isolated ASR inference time',
                    'percentiles': 'nearest-rank; descriptive development measurements, not an SLA',
                    'admission': 'authenticated streams with processing consent and configured ASR key',
                    'retention': 'last bounded window; no audio, transcript, capability or session ID'}}
