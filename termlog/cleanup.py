import time
from pathlib import Path

from termlog import config, paths


def run_cleanup(retention_days: int | None = None) -> list:
    if retention_days is None:
        retention_days = config.load_config()["retention_days"]

    logs_root = paths.get_termlog_home() / "logs"
    if not logs_root.exists():
        return []

    cutoff = time.time() - (retention_days * 86400)
    deleted = []
    for log_file in logs_root.rglob("*.log"):
        if log_file.stat().st_mtime < cutoff:
            log_file.unlink()
            deleted.append(log_file)
    return deleted
