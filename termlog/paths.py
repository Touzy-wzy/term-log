import hashlib
import os
from pathlib import Path


def get_termlog_home() -> Path:
    override = os.environ.get("TERMLOG_HOME")
    if override:
        return Path(override)
    return Path.home() / ".termlog"


def project_slug(project_path) -> str:
    normalized = str(Path(project_path).resolve())
    readable = normalized.replace(":", "").replace("\\", "--").replace("/", "--")
    readable = readable.strip("-")
    digest = hashlib.sha1(normalized.encode("utf-8")).hexdigest()[:8]
    return f"{readable}-{digest}"


def project_dir(project_path) -> Path:
    return get_termlog_home() / "logs" / project_slug(project_path)


def sessions_dir(project_path) -> Path:
    return project_dir(project_path) / "sessions"


def services_dir(project_path, service_name: str) -> Path:
    return project_dir(project_path) / "services" / service_name


def config_path() -> Path:
    return get_termlog_home() / "termlog.yaml"


def state_path() -> Path:
    return get_termlog_home() / "state.json"
