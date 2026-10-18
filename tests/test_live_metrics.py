import pytest

from callgate.live_metrics import LiveMetrics


def test_automatic_persistence_survives_reopen_and_remains_bounded(tmp_path):
    database = tmp_path / 'metrics.sqlite3'
    metrics = LiveMetrics(capacity=2, database=database)
    for value in range(3):
        metrics.record(outcome='completed', audio_ms=value,
                       first_alert_proxy_ms=None, risk_engine_ms=.1)
    restored = LiveMetrics(capacity=2, database=database)
    assert restored.summary()['sessions'] == 2
    assert restored.summary()['total_recorded'] == 3
    assert restored.summary()['evicted'] == 1
    assert restored.summary()['scope'] == 'persistent_bounded_no_content'
    assert [r['audio_ms'] for r in restored.export()['samples']] == [1, 2]
    restored.record(outcome='failed', audio_ms=4,
                    first_alert_proxy_ms=None, risk_engine_ms=None)
    assert LiveMetrics(capacity=2, database=database).summary()['total_recorded'] == 4


def test_empty_and_percentile_summary_without_content_fields():
    metrics = LiveMetrics(capacity=3)
    assert metrics.summary()['failure_rate'] is None
    metrics.record(completed=True, audio_ms=1000, first_alert_proxy_ms=100,
                   risk_engine_ms=.2)
    metrics.record(completed=False, audio_ms=2000, first_alert_proxy_ms=None,
                   risk_engine_ms=None)
    metrics.record(completed=True, audio_ms=3000, first_alert_proxy_ms=300,
                   risk_engine_ms=.4)
    metrics.record(completed=True, audio_ms=4000, first_alert_proxy_ms=200,
                   risk_engine_ms=.3)
    result = metrics.summary()
    assert result['sessions'] == 3
    assert result['completed'] == 2 and result['failed'] == 1
    assert result['failure_rate'] == pytest.approx(1/3)
    assert result['alert_proxy_p50_ms'] == 200
    assert result['alert_proxy_p95_ms'] == 300
    assert set(result).isdisjoint({'transcript', 'audio', 'challenge', 'session_id'})


@pytest.mark.parametrize('capacity', [0, -1, 1.5, 10001])
def test_capacity_is_bounded(capacity):
    with pytest.raises(ValueError):
        LiveMetrics(capacity)


def test_cancellation_does_not_inflate_failures_and_failed_alerts_do_not_skew_latency():
    metrics = LiveMetrics()
    for outcome, delay in [('cancelled', 1), ('disconnected', 2), ('failed', 3), ('completed', 900)]:
        metrics.record(outcome=outcome, audio_ms=1000, first_alert_proxy_ms=delay, risk_engine_ms=.1)
    summary = metrics.summary()
    assert summary['failure_denominator'] == 2
    assert summary['failure_rate'] == .5
    assert summary['cancelled'] == summary['disconnected'] == 1
    assert summary['alert_samples'] == 1 and summary['alert_proxy_p95_ms'] == 900
    exported = metrics.export()
    exported['samples'][0]['outcome'] = 'failed'
    assert metrics.summary()['cancelled'] == 1


@pytest.mark.parametrize('value', [float('nan'), float('inf'), -1, True, 'secret'])
def test_bad_measurements_are_rejected_without_storing(value):
    metrics = LiveMetrics()
    with pytest.raises(ValueError):
        metrics.record(outcome='completed', audio_ms=value, first_alert_proxy_ms=None, risk_engine_ms=None)
    assert metrics.summary()['sessions'] == 0
