import sys

from termlog import hook_targets, hooks


def test_discover_targets_includes_bash_and_powershell(monkeypatch, tmp_path):
    monkeypatch.setattr(hook_targets, "_home", lambda: tmp_path)
    targets = hook_targets.discover_targets()
    shells = {t["shell"] for t in targets}
    assert "bash" in shells
    assert "powershell" in shells
    assert len(targets) == 3


def test_discover_targets_includes_powershell7_profile_path(monkeypatch, tmp_path):
    monkeypatch.setattr(hook_targets, "_home", lambda: tmp_path)
    targets = hook_targets.discover_targets()
    pwsh7 = [t for t in targets if t["path"] == tmp_path / "Documents" / "PowerShell" / "Microsoft.PowerShell_profile.ps1"]
    assert len(pwsh7) == 1


def test_install_all_creates_missing_files(monkeypatch, tmp_path):
    monkeypatch.setenv("TERMLOG_HOME", str(tmp_path / "termlog_home"))
    monkeypatch.setattr(hook_targets, "_home", lambda: tmp_path)
    results = hook_targets.install_all()
    for result in results:
        assert result["path"].exists()
        content = result["path"].read_text(encoding="utf-8")
        assert "TERMLOG_SESSION" in content


def test_install_all_embeds_the_running_interpreters_absolute_path(monkeypatch, tmp_path):
    # Regression test: the hook must invoke the exact interpreter that ran
    # `termlog hook install` (guaranteed to have termlog importable), not a
    # bare "python" resolved from whatever PATH a future shell happens to
    # have. A bare "python" previously caused every newly opened terminal to
    # fail outright whenever its default python lacked termlog.
    monkeypatch.setenv("TERMLOG_HOME", str(tmp_path / "termlog_home"))
    monkeypatch.setattr(hook_targets, "_home", lambda: tmp_path)
    results = hook_targets.install_all()
    for result in results:
        content = result["path"].read_text(encoding="utf-8")
        assert " python -m termlog.recorder" not in content
        normalized_executable = sys.executable.replace("\\", "/")
        assert normalized_executable in content or sys.executable in content


def test_install_all_is_idempotent(monkeypatch, tmp_path):
    monkeypatch.setenv("TERMLOG_HOME", str(tmp_path / "termlog_home"))
    monkeypatch.setattr(hook_targets, "_home", lambda: tmp_path)
    hook_targets.install_all()
    second = hook_targets.install_all()
    assert all(result["installed"] is False for result in second)


def test_status_reflects_installed_state(monkeypatch, tmp_path):
    monkeypatch.setenv("TERMLOG_HOME", str(tmp_path / "termlog_home"))
    monkeypatch.setattr(hook_targets, "_home", lambda: tmp_path)
    before = hook_targets.status()
    assert all(result["hook_present"] is False for result in before)
    hook_targets.install_all()
    after = hook_targets.status()
    assert all(result["hook_present"] is True for result in after)


def test_uninstall_all_removes_hook(monkeypatch, tmp_path):
    monkeypatch.setenv("TERMLOG_HOME", str(tmp_path / "termlog_home"))
    monkeypatch.setattr(hook_targets, "_home", lambda: tmp_path)
    hook_targets.install_all()
    results = hook_targets.uninstall_all()
    assert all(result["removed"] is True for result in results)
    after = hook_targets.status()
    assert all(result["hook_present"] is False for result in after)


def test_install_all_marks_hook_installed_timestamp(monkeypatch, tmp_path):
    monkeypatch.setenv("TERMLOG_HOME", str(tmp_path / "termlog_home"))
    monkeypatch.setattr(hook_targets, "_home", lambda: tmp_path)
    from termlog import state

    hook_targets.install_all()
    assert state.get_hook_installed_at() is not None


def test_uninstall_all_clears_hook_installed_timestamp(monkeypatch, tmp_path):
    monkeypatch.setenv("TERMLOG_HOME", str(tmp_path / "termlog_home"))
    monkeypatch.setattr(hook_targets, "_home", lambda: tmp_path)
    from termlog import state

    hook_targets.install_all()
    hook_targets.uninstall_all()
    assert state.get_hook_installed_at() is None
