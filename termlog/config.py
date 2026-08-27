import yaml

from termlog import paths

DEFAULTS = {
    "retention_days": 60,
    "max_log_size_mb": 50,
    "services": [],
}


def load_config() -> dict:
    path = paths.config_path()
    if not path.exists():
        return dict(DEFAULTS)
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    merged = dict(DEFAULTS)
    merged.update(data)
    if merged["services"] is None:
        merged["services"] = []
    return merged


def find_service(name: str):
    for service in load_config()["services"]:
        if service["name"] == name:
            return service
    return None
