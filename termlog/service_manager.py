from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from datetime import datetime
from typing import List

from termlog import config, paths, state


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


def start(name: str, project_path: str) -> int:
    service = config.find_service(name)
    if service is None:
        raise ValueError(f"No service named '{name}' in termlog.yaml")

    if is_running(name, project_path):
        raise ValueError(f"Service '{name}' is already running")

    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S_%f")[:-3]
    log_filename = f"{name}_{timestamp}.log"

    collector_cmd = [sys.executable, "-m", "termlog.service_collector", name, project_path, log_filename]

    if sys.platform == "win32":
        process = subprocess.Popen(
            collector_cmd,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS,
            close_fds=True,
        )
    else:
        process = subprocess.Popen(
            collector_cmd,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
            close_fds=True,
        )

    log_path = paths.services_dir(project_path, name) / log_filename
    state.save_service(name, pid=process.pid, log_path=str(log_path), project_path=project_path)
    return process.pid


def stop(name: str, project_path: str, timeout: float = 5.0) -> bool:
    entry = state.get_service(name, project_path)
    if entry is None or not _is_alive(entry["pid"]):
        if entry is not None:
            state.remove_service(name, project_path)
        return False

    pid = entry["pid"]
    if sys.platform == "win32":
        subprocess.run(["taskkill", "/PID", str(pid), "/T"], capture_output=True)
    else:
        try:
            os.killpg(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass

    deadline = time.time() + timeout
    while time.time() < deadline and _is_alive(pid):
        time.sleep(0.2)

    if _is_alive(pid):
        if sys.platform == "win32":
            subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True)
        else:
            try:
                os.killpg(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        deadline = time.time() + timeout
        while time.time() < deadline and _is_alive(pid):
            time.sleep(0.2)

    state.remove_service(name, project_path)
    return True


def is_running(name: str, project_path: str) -> bool:
    entry = state.get_service(name, project_path)
    return entry is not None and _is_alive(entry["pid"])


def status(project_path: str) -> List[dict]:
    services = config.load_config()["services"]
    results = []
    for service in services:
        name = service["name"]
        entry = state.get_service(name, project_path)
        running = entry is not None and _is_alive(entry["pid"])
        results.append(
            {
                "name": name,
                "running": running,
                "pid": entry["pid"] if entry and running else None,
                "log_path": entry["log_path"] if entry and running else None,
            }
        )
    return results
