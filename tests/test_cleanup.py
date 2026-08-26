import os
import time

from termlog import cleanup, paths


def _touch_old(path, days_old):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("old log content\n", encoding="utf-8")
    old_time = time.time() - (days_old * 86400)
    os.utime(path, (old_time, old_time))


def test_deletes_files_older_than_retention(tmp_path, monkeypatch):
    monkeypatch.setenv("TERMLOG_HOME", str(tmp_path))
    old_file = paths.sessions_dir("E:/proj") / "old.log"
    _touch_old(old_file, days_old=20)

    deleted = cleanup.run_cleanup(retention_days=14)

    assert old_file in deleted
    assert not old_file.exists()


def test_keeps_files_within_retention(tmp_path, monkeypatch):
    monkeypatch.setenv("TERMLOG_HOME", str(tmp_path))
    recent_file = paths.sessions_dir("E:/proj") / "recent.log"
    _touch_old(recent_file, days_old=1)

    deleted = cleanup.run_cleanup(retention_days=14)

    assert recent_file not in deleted
    assert recent_file.exists()


def test_uses_configured_retention_when_not_specified(tmp_path, monkeypatch):
    monkeypatch.setenv("TERMLOG_HOME", str(tmp_path))
    tmp_path.mkdir(exist_ok=True)
    paths.config_path().write_text("retention_days: 5\n", encoding="utf-8")
    old_file = paths.sessions_dir("E:/proj") / "old.log"
    _touch_old(old_file, days_old=6)

    deleted = cleanup.run_cleanup()

    assert old_file in deleted


def test_returns_empty_list_when_logs_dir_missing(tmp_path, monkeypatch):
    monkeypatch.setenv("TERMLOG_HOME", str(tmp_path))
    assert cleanup.run_cleanup(retention_days=14) == []
