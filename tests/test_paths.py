import os

from termlog import paths


def test_get_termlog_home_uses_env_override(tmp_path, monkeypatch):
    monkeypatch.setenv("TERMLOG_HOME", str(tmp_path))
    assert paths.get_termlog_home() == tmp_path


def test_project_slug_is_stable(monkeypatch):
    monkeypatch.delenv("TERMLOG_HOME", raising=False)
    first = paths.project_slug("E:/log_generator")
    second = paths.project_slug("E:/log_generator")
    assert first == second
    assert "\\" not in first
    assert "/" not in first


def test_project_slug_differs_between_projects():
    assert paths.project_slug("E:/log_generator") != paths.project_slug("E:/termlog")


def test_sessions_dir_layout(tmp_path, monkeypatch):
    monkeypatch.setenv("TERMLOG_HOME", str(tmp_path))
    result = paths.sessions_dir("E:/log_generator")
    slug = paths.project_slug("E:/log_generator")
    assert result == tmp_path / "logs" / slug / "sessions"


def test_services_dir_layout(tmp_path, monkeypatch):
    monkeypatch.setenv("TERMLOG_HOME", str(tmp_path))
    result = paths.services_dir("E:/log_generator", "my-api")
    slug = paths.project_slug("E:/log_generator")
    assert result == tmp_path / "logs" / slug / "services" / "my-api"
