from termlog import state


def test_load_state_returns_empty_dict_when_missing(tmp_path, monkeypatch):
    monkeypatch.setenv("TERMLOG_HOME", str(tmp_path))
    assert state.load_state() == {}


def test_save_service_persists_entry(tmp_path, monkeypatch):
    monkeypatch.setenv("TERMLOG_HOME", str(tmp_path))
    state.save_service("my-api", pid=1234, log_path="/tmp/my-api.log")
    loaded = state.load_state()
    assert loaded["my-api"]["pid"] == 1234
    assert loaded["my-api"]["log_path"] == "/tmp/my-api.log"
    assert "started_at" in loaded["my-api"]


def test_get_service_returns_entry_or_none(tmp_path, monkeypatch):
    monkeypatch.setenv("TERMLOG_HOME", str(tmp_path))
    state.save_service("worker", pid=999, log_path="/tmp/worker.log")
    assert state.get_service("worker")["pid"] == 999
    assert state.get_service("missing") is None


def test_remove_service_deletes_entry(tmp_path, monkeypatch):
    monkeypatch.setenv("TERMLOG_HOME", str(tmp_path))
    state.save_service("worker", pid=999, log_path="/tmp/worker.log")
    state.remove_service("worker")
    assert state.get_service("worker") is None


def test_save_service_overwrites_existing_entry(tmp_path, monkeypatch):
    monkeypatch.setenv("TERMLOG_HOME", str(tmp_path))
    state.save_service("worker", pid=1, log_path="/tmp/a.log")
    state.save_service("worker", pid=2, log_path="/tmp/b.log")
    loaded = state.load_state()
    assert loaded["worker"]["pid"] == 2
    assert len(loaded) == 1
