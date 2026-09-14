import os

from termlog.recorder.session import RecordedSession, detect_shell


def test_detect_shell_from_env_shell_var(monkeypatch):
    monkeypatch.setenv("SHELL", "/usr/bin/zsh")
    assert detect_shell() == "zsh"


def test_detect_shell_defaults_when_unset(monkeypatch):
    monkeypatch.delenv("SHELL", raising=False)
    monkeypatch.delenv("COMSPEC", raising=False)
    result = detect_shell()
    assert result in ("bash", "powershell")


def test_recorded_session_start_writes_meta(tmp_path, monkeypatch):
    monkeypatch.setenv("TERMLOG_HOME", str(tmp_path))
    session = RecordedSession("E:/proj")
    session.start(shell_name="bash")
    content = session.writer.current_path.read_text(encoding="utf-8")
    assert "session_start" in content
    assert "project=E:/proj" in content
    assert "shell=bash" in content
    session.end(exit_code=0)


def test_recorded_session_end_writes_exit_code_and_closes(tmp_path, monkeypatch):
    monkeypatch.setenv("TERMLOG_HOME", str(tmp_path))
    session = RecordedSession("E:/proj")
    session.start(shell_name="bash")
    session.end(exit_code=1)
    content = session.writer.current_path.read_text(encoding="utf-8")
    assert "session_end" in content
    assert "exit_code=1" in content
    assert session.writer._fh.closed


def test_recorded_session_start_registers_active_session(tmp_path, monkeypatch):
    monkeypatch.setenv("TERMLOG_HOME", str(tmp_path))
    from termlog import state

    session = RecordedSession("E:/proj")
    session.start(shell_name="bash")

    sessions = state.list_active_sessions()
    assert len(sessions) == 1
    assert sessions[0]["pid"] == os.getpid()
    assert sessions[0]["project_path"] == "E:/proj"
    assert sessions[0]["log_path"] == str(session.writer.current_path)

    session.end(exit_code=0)


def test_recorded_session_end_clears_active_session(tmp_path, monkeypatch):
    monkeypatch.setenv("TERMLOG_HOME", str(tmp_path))
    from termlog import state

    session = RecordedSession("E:/proj")
    session.start(shell_name="bash")
    session.end(exit_code=0)

    assert state.list_active_sessions() == []
