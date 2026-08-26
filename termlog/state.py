import json
from datetime import datetime

from termlog import paths


def load_state() -> dict:
    path = paths.state_path()
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_state(data: dict) -> None:
    path = paths.state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def save_service(name: str, pid: int, log_path: str) -> None:
    data = load_state()
    data[name] = {
        "pid": pid,
        "started_at": datetime.now().isoformat(),
        "log_path": log_path,
    }
    _save_state(data)


def get_service(name: str):
    return load_state().get(name)


def remove_service(name: str) -> None:
    data = load_state()
    if name in data:
        del data[name]
        _save_state(data)
