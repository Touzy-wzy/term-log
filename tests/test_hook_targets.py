from termlog import hook_targets, hooks


def test_discover_targets_includes_bash_and_powershell(monkeypatch, tmp_path):
    monkeypatch.setattr(hook_targets, "_home", lambda: tmp_path)
    targets = hook_targets.discover_targets()
    shells = {t["shell"] for t in targets}
    assert "bash" in shells
    assert "powershell" in shells


def test_install_all_creates_missing_files(monkeypatch, tmp_path):
    monkeypatch.setattr(hook_targets, "_home", lambda: tmp_path)
    results = hook_targets.install_all()
    for result in results:
        assert result["path"].exists()
        content = result["path"].read_text(encoding="utf-8")
        assert "TERMLOG_SESSION" in content


def test_install_all_is_idempotent(monkeypatch, tmp_path):
    monkeypatch.setattr(hook_targets, "_home", lambda: tmp_path)
    hook_targets.install_all()
    second = hook_targets.install_all()
    assert all(result["installed"] is False for result in second)


def test_status_reflects_installed_state(monkeypatch, tmp_path):
    monkeypatch.setattr(hook_targets, "_home", lambda: tmp_path)
    before = hook_targets.status()
    assert all(result["hook_present"] is False for result in before)
    hook_targets.install_all()
    after = hook_targets.status()
    assert all(result["hook_present"] is True for result in after)


def test_uninstall_all_removes_hook(monkeypatch, tmp_path):
    monkeypatch.setattr(hook_targets, "_home", lambda: tmp_path)
    hook_targets.install_all()
    results = hook_targets.uninstall_all()
    assert all(result["removed"] is True for result in results)
    after = hook_targets.status()
    assert all(result["hook_present"] is False for result in after)
