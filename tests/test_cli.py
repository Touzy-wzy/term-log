from unittest.mock import patch

from termlog.cli import main


def test_hook_install_calls_install_all(tmp_path, monkeypatch):
    monkeypatch.setenv("TERMLOG_HOME", str(tmp_path))
    with patch("termlog.hook_targets.install_all", return_value=[]) as mock_install:
        exit_code = main(["hook", "install"])
    assert exit_code == 0
    assert mock_install.called


def test_hook_uninstall_exports_logs_before_uninstalling(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("TERMLOG_HOME", str(tmp_path))
    with patch("termlog.log_export.export_session_logs", return_value=[tmp_path / "a.log"]) as mock_export, patch(
        "termlog.hook_targets.uninstall_all", return_value=[]
    ) as mock_uninstall:
        exit_code = main(["hook", "uninstall"])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert mock_export.called
    assert mock_uninstall.called
    assert "exported 1" in captured.out


def test_hook_status_calls_status(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("TERMLOG_HOME", str(tmp_path))
    fake_result = [{"shell": "bash", "path": tmp_path / ".bashrc", "hook_present": True}]
    with patch("termlog.hook_targets.status", return_value=fake_result):
        exit_code = main(["hook", "status"])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "bash" in captured.out


def test_service_start_calls_service_manager(tmp_path, monkeypatch):
    monkeypatch.setenv("TERMLOG_HOME", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    with patch("termlog.service_manager.start", return_value=1234) as mock_start:
        exit_code = main(["service", "start", "my-api"])
    assert exit_code == 0
    mock_start.assert_called_once_with("my-api", str(tmp_path))


def test_service_start_reports_unknown_service(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("TERMLOG_HOME", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    with patch("termlog.service_manager.start", side_effect=ValueError("No service named 'missing'")):
        exit_code = main(["service", "start", "missing"])
    captured = capsys.readouterr()
    assert exit_code == 1
    assert "missing" in captured.err


def test_service_start_all_starts_every_configured_service(tmp_path, monkeypatch):
    monkeypatch.setenv("TERMLOG_HOME", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    fake_config = {
        "retention_days": 14,
        "max_log_size_mb": 50,
        "services": [{"name": "my-api"}, {"name": "my-worker"}],
    }
    with patch("termlog.config.load_config", return_value=fake_config), patch(
        "termlog.service_manager.start", side_effect=[1234, 5678]
    ) as mock_start:
        exit_code = main(["service", "start", "--all"])
    assert exit_code == 0
    assert mock_start.call_count == 2
    mock_start.assert_any_call("my-api", str(tmp_path))
    mock_start.assert_any_call("my-worker", str(tmp_path))


def test_service_stop_calls_service_manager(tmp_path, monkeypatch):
    monkeypatch.setenv("TERMLOG_HOME", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    with patch("termlog.service_manager.stop", return_value=True) as mock_stop:
        exit_code = main(["service", "stop", "my-api"])
    assert exit_code == 0
    mock_stop.assert_called_once_with("my-api", str(tmp_path))


def test_service_status_prints_table(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("TERMLOG_HOME", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    fake_status = [{"name": "my-api", "running": True, "pid": 1234, "log_path": "/tmp/my-api.log"}]
    with patch("termlog.service_manager.status", return_value=fake_status) as mock_status:
        exit_code = main(["service", "status"])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "my-api" in captured.out
    assert "1234" in captured.out
    mock_status.assert_called_once_with(str(tmp_path))


def test_every_invocation_runs_cleanup(tmp_path, monkeypatch):
    monkeypatch.setenv("TERMLOG_HOME", str(tmp_path))
    with patch("termlog.cleanup.run_cleanup", return_value=[]) as mock_cleanup, patch(
        "termlog.hook_targets.status", return_value=[]
    ):
        main(["hook", "status"])
    assert mock_cleanup.called


def test_log_view_prints_ansi_stripped_content(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("TERMLOG_HOME", str(tmp_path))
    log_file = tmp_path / "session.log"
    log_file.write_text("\x1b[93mhello\x1b[m world\n", encoding="utf-8")

    exit_code = main(["log", "view", str(log_file)])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.out == "hello world\n"
    assert "\x1b" not in captured.out


def test_log_view_writes_to_out_file_when_given(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("TERMLOG_HOME", str(tmp_path))
    log_file = tmp_path / "session.log"
    log_file.write_text("\x1b[93mhello\x1b[m world\n", encoding="utf-8")
    out_file = tmp_path / "session.clean.log"

    exit_code = main(["log", "view", str(log_file), "--out", str(out_file)])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert out_file.read_text(encoding="utf-8") == "hello world\n"
    assert str(out_file) in captured.out


def test_log_view_reports_missing_file(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("TERMLOG_HOME", str(tmp_path))
    missing = tmp_path / "does_not_exist.log"

    exit_code = main(["log", "view", str(missing)])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "could not read" in captured.err
