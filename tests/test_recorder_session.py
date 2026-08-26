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
