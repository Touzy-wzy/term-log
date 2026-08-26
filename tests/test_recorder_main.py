import sys
from unittest.mock import patch, MagicMock

from termlog.recorder.__main__ import main


def test_main_delegates_to_platform_backend_and_returns_exit_code(tmp_path, monkeypatch):
    monkeypatch.setenv("TERMLOG_HOME", str(tmp_path))
    monkeypatch.setenv("SHELL", "/bin/bash")
    monkeypatch.chdir(tmp_path)

    backend_module = "termlog.recorder.unix_backend" if sys.platform != "win32" else "termlog.recorder.windows_backend"

    # Mock RecordedSession to avoid filesystem operations
    mock_session = MagicMock()
    with patch("termlog.recorder.__main__.RecordedSession", return_value=mock_session) as mock_session_cls:
        with patch(f"{backend_module}.run", return_value=42) as mock_run:
            with patch("termlog.recorder.__main__.cleanup.run_cleanup", return_value=[]) as mock_cleanup:
                exit_code = main()

    assert exit_code == 42
    assert mock_session.start.called
    assert mock_session.end.called
    assert mock_run.called
    assert mock_cleanup.called
    command_arg = mock_run.call_args[0][0]
    assert isinstance(command_arg, list)
    assert len(command_arg) >= 1


def test_main_runs_cleanup_after_session_ends(tmp_path, monkeypatch):
    monkeypatch.setenv("TERMLOG_HOME", str(tmp_path))
    monkeypatch.setenv("SHELL", "/bin/bash")
    monkeypatch.chdir(tmp_path)

    backend_module = "termlog.recorder.unix_backend" if sys.platform != "win32" else "termlog.recorder.windows_backend"

    call_order = []
    mock_session = MagicMock()
    mock_session.end.side_effect = lambda **kwargs: call_order.append("session_end")

    with patch("termlog.recorder.__main__.RecordedSession", return_value=mock_session):
        with patch(f"{backend_module}.run", return_value=0):
            with patch(
                "termlog.recorder.__main__.cleanup.run_cleanup",
                side_effect=lambda **kwargs: call_order.append("cleanup") or [],
            ):
                main()

    assert call_order == ["session_end", "cleanup"]
