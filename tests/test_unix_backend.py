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


def test_run_syncs_pty_size_on_startup_and_on_sigwinch(tmp_path, monkeypatch):
    # Regression test: pty.fork() doesn't size the new pty to match the
    # real terminal, so the captured child shell starts out computing
    # redraw cursor positions against the wrong size until resized. A real
    # window resize afterwards delivers SIGWINCH, which should re-sync too.
    monkeypatch.setenv("TERMLOG_HOME", str(tmp_path))
    import os
    import signal

    from termlog.recorder import unix_backend
    from termlog.recorder.session import RecordedSession

    sync_calls = []
    monkeypatch.setattr(unix_backend, "_sync_pty_size", lambda master_fd: sync_calls.append(master_fd))
    handler_before = signal.getsignal(signal.SIGWINCH)

    session = RecordedSession("E:/proj")
    session.start(shell_name="bash")

    exit_code = unix_backend.run(
        ["sh", "-c", "kill -WINCH $PPID; sleep 0.2"], session
    )
    session.end(exit_code=exit_code)

    assert exit_code == 0
    # Once at startup, and at least once more from the SIGWINCH the child sent.
    assert len(sync_calls) >= 2
    assert signal.getsignal(signal.SIGWINCH) == handler_before
