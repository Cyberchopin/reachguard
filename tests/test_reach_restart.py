"""Restart guard tests never signal a real service or access private runtime."""
import os
from pathlib import Path
import pytest
from scripts import restart_reach_observed as restart


def test_listening_before_telemetry_initialization_is_not_failure(tmp_path, monkeypatch):
    logfile = tmp_path/'service.log'
    logfile.write_bytes(b'old startup\n'+restart.MARKER+b'\n')
    offset = logfile.stat().st_size
    monkeypatch.setattr(restart, 'listeners', lambda port: 'LISTEN pid=123,')
    monkeypatch.setattr(restart, 'http', lambda *args, **kwargs: (200, b''))
    assert restart.startup_ready(tmp_path, 8783, 123, offset) is False
    with logfile.open('ab') as log:
        log.write(restart.MARKER+b'\n')
    assert restart.startup_ready(tmp_path, 8783, 123, offset) is True


def test_marker_and_listen_require_http_ready_too(tmp_path, monkeypatch):
    (tmp_path/'service.log').write_bytes(restart.MARKER)
    monkeypatch.setattr(restart, 'listeners', lambda port: 'LISTEN pid=123,')
    def unavailable(*args, **kwargs):
        raise TimeoutError()
    monkeypatch.setattr(restart, 'http', unavailable)
    assert restart.startup_ready(tmp_path, 8783, 123, 0) is False
    monkeypatch.setattr(restart, 'http', lambda *args, **kwargs: (200, b''))
    assert restart.startup_ready(tmp_path, 8783, 123, 0) is True


def test_unknown_listener_is_never_stopped(tmp_path, monkeypatch):
    monkeypatch.setattr(restart, 'listeners', lambda port: 'LISTEN 127.0.0.1:8780 pid=123,')
    with pytest.raises(SystemExit, match='missing PID file'):
        restart.owned_process(tmp_path, 8780, 'scripts.start_device_events')


def test_pid_must_own_the_port(tmp_path, monkeypatch):
    (tmp_path/'service.pid').write_text(str(os.getpid()))
    monkeypatch.setattr(restart, 'listeners', lambda port: 'LISTEN 127.0.0.1:8780 pid=999999,')
    with pytest.raises(SystemExit, match='unexpected listener ownership'):
        restart.owned_process(tmp_path, 8780, 'scripts.start_device_events')


def test_pid_with_wrong_command_is_rejected(tmp_path, monkeypatch):
    pid = os.getpid()
    (tmp_path/'service.pid').write_text(str(pid))
    monkeypatch.setattr(restart, 'ROOT', Path.cwd())
    monkeypatch.setattr(restart, 'listeners', lambda port: f'LISTEN 127.0.0.1:8780 pid={pid},')
    with pytest.raises(SystemExit, match='not the expected launcher'):
        restart.owned_process(tmp_path, 8780, 'scripts.start_device_events')


def test_missing_exported_dsn_aborts_before_process_operations(tmp_path, monkeypatch):
    device = tmp_path/'device';help_dir = tmp_path/'help'
    device.mkdir();help_dir.mkdir()
    for parent,names in [(device, ('device.token','viewer.token','events.sqlite3')),
                         (help_dir, ('credentials.json','owner.token','contact.token','dashboard.token','help.sqlite3'))]:
        for name in names:
            (parent/name).touch()
    monkeypatch.setattr(restart, 'D', device)
    monkeypatch.setattr(restart, 'H', help_dir)
    monkeypatch.setattr(restart.sys, 'argv', ['restart_reach_observed'])
    monkeypatch.delenv('CALLGATE_SENTRY_DSN', raising=False)
    monkeypatch.setattr(restart.os, 'kill', lambda *args: pytest.fail('must not signal a process'))
    with pytest.raises(SystemExit, match='Export CALLGATE_SENTRY_DSN'):
        restart.main()
