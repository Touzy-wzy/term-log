import gc
import sys
import time

import pytest

from termlog import config, paths, service_manager, state


def _write_config(tmp_path, services):
    tmp_path.mkdir(exist_ok=True)
    lines = ["services:"]
    for s in services:
        lines.append(f"  - name: {s['name']}")
        lines.append(f"    command: {s['command']}")
        lines.append(f"    cwd: {s['cwd']}")
    paths.config_path().write_text("\n".join(lines) + "\n", encoding="utf-8")


LONG_RUNNING_CMD = (
    "python -c \"import time; [print('tick', flush=True) or time.sleep(0.2) for _ in range(50)]\""
)
QUICK_CMD = "python -c \"print('done', flush=True)\""


def test_start_raises_for_unknown_service(tmp_path, monkeypatch):
    monkeypatch.setenv("TERMLOG_HOME", str(tmp_path))
    _write_config(tmp_path, [])
    with pytest.raises(ValueError):
        service_manager.start("missing", "E:/proj")


def test_start_launches_process_and_persists_state(tmp_path, monkeypatch):
    monkeypatch.setenv("TERMLOG_HOME", str(tmp_path))
    _write_config(tmp_path, [{"name": "ticker", "command": LONG_RUNNING_CMD, "cwd": str(tmp_path)}])

    pid = service_manager.start("ticker", "E:/proj")
    try:
        assert pid > 0
        entry = state.get_service("ticker")
        assert entry["pid"] == pid
    finally:
        service_manager.stop("ticker")


def test_start_captures_output_to_log(tmp_path, monkeypatch):
    monkeypatch.setenv("TERMLOG_HOME", str(tmp_path))
    _write_config(tmp_path, [{"name": "ticker", "command": LONG_RUNNING_CMD, "cwd": str(tmp_path)}])

    service_manager.start("ticker", "E:/proj")
    try:
        time.sleep(2.0)
        entry = state.get_service("ticker")
        content = open(entry["log_path"], encoding="utf-8", errors="replace").read()
        assert "tick" in content
        assert "service_start" in content
    finally:
        service_manager.stop("ticker")


def test_log_records_exit_code_when_process_finishes_on_its_own(tmp_path, monkeypatch):
    monkeypatch.setenv("TERMLOG_HOME", str(tmp_path))
    _write_config(tmp_path, [{"name": "quick", "command": QUICK_CMD, "cwd": str(tmp_path)}])

    service_manager.start("quick", "E:/proj")
    entry = state.get_service("quick")
    log_path = entry["log_path"]

    deadline = time.time() + 8
    content = ""
    while time.time() < deadline:
        try:
            content = open(log_path, encoding="utf-8", errors="replace").read()
        except FileNotFoundError:
            content = ""
        if "service_exit" in content:
            break
        time.sleep(0.2)

    assert "service_exit" in content
    assert "exit_code=0" in content


def test_service_survives_after_start_return_value_is_dropped(tmp_path, monkeypatch):
    monkeypatch.setenv("TERMLOG_HOME", str(tmp_path))
    _write_config(tmp_path, [{"name": "ticker", "command": LONG_RUNNING_CMD, "cwd": str(tmp_path)}])

    service_manager.start("ticker", "E:/proj")
    gc.collect()  # drop any Popen object references this process might still hold

    try:
        time.sleep(2.0)
        entry = state.get_service("ticker")
        content = open(entry["log_path"], encoding="utf-8", errors="replace").read()
        assert "tick" in content
        assert "service_exit" not in content  # still running, hasn't finished its 50-tick loop
    finally:
        service_manager.stop("ticker")


def test_stop_terminates_running_process(tmp_path, monkeypatch):
    monkeypatch.setenv("TERMLOG_HOME", str(tmp_path))
    _write_config(tmp_path, [{"name": "ticker", "command": LONG_RUNNING_CMD, "cwd": str(tmp_path)}])

    service_manager.start("ticker", "E:/proj")
    stopped = service_manager.stop("ticker")

    assert stopped is True
    assert state.get_service("ticker") is None


def test_stop_returns_false_when_not_running(tmp_path, monkeypatch):
    monkeypatch.setenv("TERMLOG_HOME", str(tmp_path))
    assert service_manager.stop("never-started") is False


def test_status_reports_running_and_stopped_services(tmp_path, monkeypatch):
    monkeypatch.setenv("TERMLOG_HOME", str(tmp_path))
    _write_config(
        tmp_path,
        [
            {"name": "ticker", "command": LONG_RUNNING_CMD, "cwd": str(tmp_path)},
            {"name": "idle", "command": QUICK_CMD, "cwd": str(tmp_path)},
        ],
    )

    service_manager.start("ticker", "E:/proj")
    try:
        report = {entry["name"]: entry for entry in service_manager.status()}
        assert report["ticker"]["running"] is True
        assert report["idle"]["running"] is False
    finally:
        service_manager.stop("ticker")
