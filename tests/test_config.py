from termlog import config, paths


def test_load_config_returns_defaults_when_missing(tmp_path, monkeypatch):
    monkeypatch.setenv("TERMLOG_HOME", str(tmp_path))
    cfg = config.load_config()
    assert cfg["retention_days"] == 14
    assert cfg["max_log_size_mb"] == 50
    assert cfg["services"] == []


def test_load_config_reads_yaml_file(tmp_path, monkeypatch):
    monkeypatch.setenv("TERMLOG_HOME", str(tmp_path))
    tmp_path.mkdir(exist_ok=True)
    cfg_file = paths.config_path()
    cfg_file.write_text(
        "retention_days: 7\n"
        "max_log_size_mb: 10\n"
        "services:\n"
        "  - name: my-api\n"
        "    command: python app.py\n"
        "    cwd: E:/my-project\n",
        encoding="utf-8",
    )
    cfg = config.load_config()
    assert cfg["retention_days"] == 7
    assert cfg["max_log_size_mb"] == 10
    assert cfg["services"][0]["name"] == "my-api"


def test_find_service_returns_matching_entry(tmp_path, monkeypatch):
    monkeypatch.setenv("TERMLOG_HOME", str(tmp_path))
    tmp_path.mkdir(exist_ok=True)
    paths.config_path().write_text(
        "services:\n  - name: worker\n    command: npm run worker\n    cwd: E:/proj\n",
        encoding="utf-8",
    )
    found = config.find_service("worker")
    assert found["command"] == "npm run worker"
    assert config.find_service("missing") is None
