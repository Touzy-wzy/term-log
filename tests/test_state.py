from termlog import paths, state


def test_load_state_returns_empty_dict_when_missing(tmp_path, monkeypatch):
    monkeypatch.setenv("TERMLOG_HOME", str(tmp_path))
    assert state.load_state() == {}


def test_save_service_persists_entry(tmp_path, monkeypatch):
    monkeypatch.setenv("TERMLOG_HOME", str(tmp_path))
    state.save_service("my-api", pid=1234, log_path="/tmp/my-api.log", project_path="E:/proj")
    loaded = state.load_state()
    key = "E:/proj::my-api"
    assert loaded[key]["pid"] == 1234
    assert loaded[key]["log_path"] == "/tmp/my-api.log"
    assert "started_at" in loaded[key]


def test_get_service_returns_entry_or_none(tmp_path, monkeypatch):
    monkeypatch.setenv("TERMLOG_HOME", str(tmp_path))
    state.save_service("worker", pid=999, log_path="/tmp/worker.log", project_path="E:/proj")
    assert state.get_service("worker", "E:/proj")["pid"] == 999
    assert state.get_service("missing", "E:/proj") is None


def test_remove_service_deletes_entry(tmp_path, monkeypatch):
    monkeypatch.setenv("TERMLOG_HOME", str(tmp_path))
    state.save_service("worker", pid=999, log_path="/tmp/worker.log", project_path="E:/proj")
    state.remove_service("worker", "E:/proj")
    assert state.get_service("worker", "E:/proj") is None


def test_save_service_overwrites_existing_entry(tmp_path, monkeypatch):
    monkeypatch.setenv("TERMLOG_HOME", str(tmp_path))
    state.save_service("worker", pid=1, log_path="/tmp/a.log", project_path="E:/proj")
    state.save_service("worker", pid=2, log_path="/tmp/b.log", project_path="E:/proj")
    loaded = state.load_state()
    assert loaded["E:/proj::worker"]["pid"] == 2
    assert len(loaded) == 1


def test_same_service_name_in_different_projects_does_not_collide(tmp_path, monkeypatch):
    monkeypatch.setenv("TERMLOG_HOME", str(tmp_path))
    state.save_service("api", pid=1, log_path="/a.log", project_path="/proj1")
    state.save_service("api", pid=2, log_path="/b.log", project_path="/proj2")
    assert state.get_service("api", "/proj1")["pid"] == 1
    assert state.get_service("api", "/proj2")["pid"] == 2


def test_load_state_returns_empty_dict_when_file_is_corrupted(tmp_path, monkeypatch):
    monkeypatch.setenv("TERMLOG_HOME", str(tmp_path))
    path = paths.state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{not valid json", encoding="utf-8")
    assert state.load_state() == {}


def test_save_then_load_round_trip_still_works(tmp_path, monkeypatch):
    monkeypatch.setenv("TERMLOG_HOME", str(tmp_path))
    state.save_service("roundtrip", pid=42, log_path="/x.log", project_path="E:/proj")
    loaded = state.load_state()
    assert loaded["E:/proj::roundtrip"]["pid"] == 42
    assert loaded["E:/proj::roundtrip"]["log_path"] == "/x.log"


def test_get_hook_installed_at_returns_none_when_never_marked(tmp_path, monkeypatch):
    monkeypatch.setenv("TERMLOG_HOME", str(tmp_path))
    assert state.get_hook_installed_at() is None


def test_mark_hook_installed_records_timestamp(tmp_path, monkeypatch):
    monkeypatch.setenv("TERMLOG_HOME", str(tmp_path))
    state.mark_hook_installed()
    assert state.get_hook_installed_at() is not None


def test_mark_hook_installed_does_not_reset_existing_timestamp(tmp_path, monkeypatch):
    monkeypatch.setenv("TERMLOG_HOME", str(tmp_path))
    state.mark_hook_installed()
    first = state.get_hook_installed_at()
    state.mark_hook_installed()
    assert state.get_hook_installed_at() == first


def test_clear_hook_installed_at_removes_timestamp(tmp_path, monkeypatch):
    monkeypatch.setenv("TERMLOG_HOME", str(tmp_path))
    state.mark_hook_installed()
    state.clear_hook_installed_at()
    assert state.get_hook_installed_at() is None
