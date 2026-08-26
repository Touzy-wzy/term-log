import sys

import pytest

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="Windows PTY backend only")


def test_run_captures_noninteractive_command_output(tmp_path, monkeypatch):
    monkeypatch.setenv("TERMLOG_HOME", str(tmp_path))
    from termlog.recorder import windows_backend
    from termlog.recorder.session import RecordedSession

    session = RecordedSession("E:/proj")
    session.start(shell_name="powershell")
    log_path = session.writer.current_path

    exit_code = windows_backend.run(
        ["powershell", "-NoProfile", "-Command", "Write-Output 'hello from termlog'"], session
    )
    session.end(exit_code=exit_code)

    content = log_path.read_text(encoding="utf-8", errors="replace")
    assert exit_code == 0
    assert "hello from termlog" in content


def test_run_does_not_drop_output_that_arrives_right_before_exit(tmp_path, monkeypatch):
    # Regression test: pywinpty relays child output to its socket via a
    # background thread that can lag slightly behind the pty reporting the
    # process as dead. Repeated runs previously dropped the process's
    # actual output (only the terminal setup escape codes made it through)
    # often enough to be a real flake, not a one-off. Run several times in
    # one test to catch a regression that only shows up intermittently.
    monkeypatch.setenv("TERMLOG_HOME", str(tmp_path))
    from termlog.recorder import windows_backend
    from termlog.recorder.session import RecordedSession

    for _ in range(10):
        session = RecordedSession("E:/proj")
        session.start(shell_name="powershell")
        log_path = session.writer.current_path

        exit_code = windows_backend.run(
            ["powershell", "-NoProfile", "-Command", "Write-Output 'hello from termlog'"], session
        )
        session.end(exit_code=exit_code)

        content = log_path.read_text(encoding="utf-8", errors="replace")
        assert exit_code == 0
        assert "hello from termlog" in content


def test_run_returns_nonzero_exit_code_on_failure(tmp_path, monkeypatch):
    monkeypatch.setenv("TERMLOG_HOME", str(tmp_path))
    from termlog.recorder import windows_backend
    from termlog.recorder.session import RecordedSession

    session = RecordedSession("E:/proj")
    session.start(shell_name="powershell")
    exit_code = windows_backend.run(
        ["powershell", "-NoProfile", "-Command", "exit 3"], session
    )
    session.end(exit_code=exit_code)

    assert exit_code == 3
