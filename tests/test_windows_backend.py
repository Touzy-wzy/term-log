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


def test_run_resizes_the_pty_when_the_real_console_is_resized_mid_session(tmp_path, monkeypatch):
    # Regression test: PtyProcess.spawn() is only given the console's size
    # once, at startup. If the user resizes the real terminal window
    # mid-session (very common — e.g. dragging a VS Code panel), the
    # captured child shell never finds out and keeps computing redraw
    # cursor positions against the stale size, reproducing the exact
    # garbled-output bug that passing the initial size fixed for the
    # startup-only case.
    monkeypatch.setenv("TERMLOG_HOME", str(tmp_path))
    import socket as socket_module

    from termlog.recorder import windows_backend
    from termlog.recorder.session import RecordedSession

    call_count = [0]

    def fake_get_console_dimensions():
        # First call is the initial spawn size. Every call after that
        # simulates the user having resized the real window.
        call_count[0] += 1
        return (24, 80) if call_count[0] <= 1 else (30, 120)

    monkeypatch.setattr(windows_backend, "get_console_dimensions", fake_get_console_dimensions)

    fake_now = [0.0]
    monkeypatch.setattr(windows_backend.time, "monotonic", lambda: fake_now[0])

    class FakeFileobj:
        def settimeout(self, value):
            pass

    class FakeProcess:
        def __init__(self):
            self.exitstatus = 0
            self.resize_calls = []
            self.fileobj = FakeFileobj()
            self._reads = 0

        def isalive(self):
            return self._reads < 2

        def read(self, size=1024):
            self._reads += 1
            fake_now[0] += windows_backend.RESIZE_CHECK_INTERVAL_SECONDS
            if self._reads >= 2:
                raise EOFError()
            raise socket_module.timeout()

        def write(self, data):
            pass

        def setwinsize(self, rows, cols):
            self.resize_calls.append((rows, cols))

        def wait(self):
            return self.exitstatus

    fake_process = FakeProcess()
    monkeypatch.setattr(windows_backend.PtyProcess, "spawn", staticmethod(lambda *a, **k: fake_process))

    session = RecordedSession("E:/proj")
    session.start(shell_name="powershell")
    windows_backend.run(["powershell"], session)
    session.end(exit_code=0)

    assert (30, 120) in fake_process.resize_calls


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
