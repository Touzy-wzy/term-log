from __future__ import annotations

from datetime import datetime
from pathlib import Path

from termlog import ansi, paths, state


def _export_dir(source_dir: Path, dest_dir: Path, cutoff: float) -> list[Path]:
    if not source_dir.exists():
        return []

    exported = []
    for log_file in source_dir.glob("*.log"):
        if log_file.stat().st_mtime < cutoff:
            continue
        try:
            raw = log_file.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        cleaned = ansi.strip_ansi(raw)
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_path = dest_dir / log_file.name
        dest_path.write_text(cleaned, encoding="utf-8")
        exported.append(dest_path)
    return exported


def export_session_logs() -> list[Path]:
    installed_at = state.get_hook_installed_at()
    if not installed_at:
        return []
    cutoff = datetime.fromisoformat(installed_at).timestamp()

    logs_root = paths.get_termlog_home() / "logs"
    if not logs_root.exists():
        return []

    exported = []
    for project_dir in logs_root.iterdir():
        if not project_dir.is_dir():
            continue

        exported.extend(_export_dir(project_dir / "sessions", project_dir / "sessions_view", cutoff))

        services_root = project_dir / "services"
        if services_root.exists():
            for service_dir in services_root.iterdir():
                if not service_dir.is_dir():
                    continue
                dest_dir = project_dir / "services_view" / service_dir.name
                exported.extend(_export_dir(service_dir, dest_dir, cutoff))

    return exported
