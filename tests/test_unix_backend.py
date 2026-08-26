import sys

import pytest

pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="Unix PTY backend only")


def test_run_captures_noninteractive_command_output(tmp_path, monkeypatch):
    monkeypatch.setenv("TERMLOG_HOME", str(tmp_path))
    from termlog.recorder import unix_backend
    from termlog.recorder.session import RecordedSession

    session = RecordedSession("E:/proj")
    session.start(shell_name="bash")
    log_path = session.writer.current_path

    exit_code = unix_backend.run(["echo", "hello from termlog"], session)
    session.end(exit_code=exit_code)

    content = log_path.read_text(encoding="utf-8", errors="replace")
    assert exit_code == 0
    assert "hello from termlog" in content


def test_run_returns_nonzero_exit_code_on_failure(tmp_path, monkeypatch):
    monkeypatch.setenv("TERMLOG_HOME", str(tmp_path))
    from termlog.recorder import unix_backend
    from termlog.recorder.session import RecordedSession

    session = RecordedSession("E:/proj")
    session.start(shell_name="bash")
    exit_code = unix_backend.run(["sh", "-c", "exit 3"], session)
    session.end(exit_code=exit_code)

    assert exit_code == 3
