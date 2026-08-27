import os
import time

from termlog import log_export, paths, state


def _write_log(path, content, mtime_offset_seconds=0):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    if mtime_offset_seconds:
        stamp = time.time() + mtime_offset_seconds
        os.utime(path, (stamp, stamp))


def test_returns_empty_list_when_hook_never_installed(tmp_path, monkeypatch):
    monkeypatch.setenv("TERMLOG_HOME", str(tmp_path))
    session_log = paths.sessions_dir("E:/proj") / "session_1.log"
    _write_log(session_log, "\x1b[93mhello\x1b[m\n")

    assert log_export.export_session_logs() == []


def test_exports_session_log_created_after_install(tmp_path, monkeypatch):
    monkeypatch.setenv("TERMLOG_HOME", str(tmp_path))
    state.mark_hook_installed()
    session_log = paths.sessions_dir("E:/proj") / "session_1.log"
    _write_log(session_log, "\x1b[93mhello\x1b[m world\n")

    exported = log_export.export_session_logs()

    dest = paths.project_dir("E:/proj") / "sessions_view" / "session_1.log"
    assert dest in exported
    assert dest.read_text(encoding="utf-8") == "hello world\n"
    # original untouched
    assert "\x1b" in session_log.read_text(encoding="utf-8")


def test_skips_session_log_older_than_install_time(tmp_path, monkeypatch):
    monkeypatch.setenv("TERMLOG_HOME", str(tmp_path))
    old_log = paths.sessions_dir("E:/proj") / "old.log"
    _write_log(old_log, "old content\n", mtime_offset_seconds=-3600)
    state.mark_hook_installed()

    exported = log_export.export_session_logs()

    assert exported == []
    dest = paths.project_dir("E:/proj") / "sessions_view" / "old.log"
    assert not dest.exists()


def test_exports_service_logs_across_service_names(tmp_path, monkeypatch):
    monkeypatch.setenv("TERMLOG_HOME", str(tmp_path))
    state.mark_hook_installed()
    service_log = paths.services_dir("E:/proj", "my-api") / "my-api_1.log"
    _write_log(service_log, "\x1b[32mok\x1b[m\n")

    exported = log_export.export_session_logs()

    dest = paths.project_dir("E:/proj") / "services_view" / "my-api" / "my-api_1.log"
    assert dest in exported
    assert dest.read_text(encoding="utf-8") == "ok\n"


def test_exports_across_multiple_projects(tmp_path, monkeypatch):
    monkeypatch.setenv("TERMLOG_HOME", str(tmp_path))
    state.mark_hook_installed()
    log_a = paths.sessions_dir("E:/proj_a") / "a.log"
    log_b = paths.sessions_dir("E:/proj_b") / "b.log"
    _write_log(log_a, "from a\n")
    _write_log(log_b, "from b\n")

    exported = log_export.export_session_logs()

    assert len(exported) == 2


def test_returns_empty_list_when_logs_dir_missing(tmp_path, monkeypatch):
    monkeypatch.setenv("TERMLOG_HOME", str(tmp_path))
    state.mark_hook_installed()
    assert log_export.export_session_logs() == []
