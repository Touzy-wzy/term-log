import json
import os
import subprocess
import sys
from datetime import datetime

from termlog import paths


def _state_key(name: str, project_path: str) -> str:
    return f"{project_path}::{name}"


def load_state() -> dict:
    path = paths.state_path()
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except (json.JSONDecodeError, ValueError):
            return {}


def _save_state(data: dict) -> None:
    path = paths.state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(".json.tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp_path, path)


def save_service(name: str, pid: int, log_path: str, project_path: str) -> None:
    data = load_state()
    data[_state_key(name, project_path)] = {
        "pid": pid,
        "started_at": datetime.now().isoformat(),
        "log_path": log_path,
    }
    _save_state(data)


def get_service(name: str, project_path: str):
    return load_state().get(_state_key(name, project_path))


def remove_service(name: str, project_path: str) -> None:
    data = load_state()
    key = _state_key(name, project_path)
    if key in data:
        del data[key]
        _save_state(data)


def _is_alive(pid: int) -> bool:
    if sys.platform == "win32":
        result = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}"],
            capture_output=True,
            text=True,
        )
        return str(pid) in result.stdout
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False


def save_active_session(pid: int, log_path: str, project_path: str) -> None:
    data = load_state()
    sessions = data.setdefault("active_sessions", {})
    sessions[str(pid)] = {
        "project_path": project_path,
        "log_path": log_path,
        "started_at": datetime.now().isoformat(),
    }
    _save_state(data)


def remove_active_session(pid: int) -> None:
    data = load_state()
    sessions = data.get("active_sessions", {})
    key = str(pid)
    if key in sessions:
        del sessions[key]
        _save_state(data)


def _last_activity_at(log_path: str):
    try:
        mtime = os.path.getmtime(log_path)
    except OSError:
        return None
    return datetime.fromtimestamp(mtime).isoformat()


def list_active_sessions() -> list:
    data = load_state()
    sessions = data.get("active_sessions", {})
    live = []
    stale_pids = []
    for pid_str, entry in sessions.items():
        pid = int(pid_str)
        if _is_alive(pid):
            live.append(
                {
                    "pid": pid,
                    "project_path": entry["project_path"],
                    "log_path": entry["log_path"],
                    "started_at": entry["started_at"],
                    "last_activity_at": _last_activity_at(entry["log_path"]),
                }
            )
        else:
            stale_pids.append(pid_str)

    if stale_pids:
        data = load_state()
        sessions = data.get("active_sessions", {})
        for pid_str in stale_pids:
            sessions.pop(pid_str, None)
        _save_state(data)

    return live


def get_hook_installed_at():
    return load_state().get("hook_installed_at")


def mark_hook_installed() -> None:
    data = load_state()
    if "hook_installed_at" not in data:
        data["hook_installed_at"] = datetime.now().isoformat()
        _save_state(data)


def clear_hook_installed_at() -> None:
    data = load_state()
    if "hook_installed_at" in data:
        del data["hook_installed_at"]
        _save_state(data)
