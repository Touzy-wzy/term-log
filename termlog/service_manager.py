from __future__ import annotations

import os
import shlex
import signal
import subprocess
import sys
import threading
import time
from typing import List, Optional

from termlog import config, paths, state
from termlog.storage import LineBuffer, LogWriter


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


def _pump_output(process: subprocess.Popen, writer: LogWriter, line_buffer: LineBuffer) -> None:
    for stream in (process.stdout, process.stderr):
        if stream is None:
            continue
        for raw_line in stream:
            line_buffer.feed(raw_line if isinstance(raw_line, bytes) else raw_line.encode("utf-8"))
    line_buffer.flush()

    exit_code = process.wait()
    writer.write_meta("service_exit", exit_code=exit_code)
    writer.close()


def start(name: str, project_path: str) -> int:
    service = config.find_service(name)
    if service is None:
        raise ValueError(f"No service named '{name}' in termlog.yaml")

    max_size_mb = config.load_config()["max_log_size_mb"]
    writer = LogWriter(paths.services_dir(project_path, name), prefix=name, max_size_mb=max_size_mb)
    line_buffer = LineBuffer(writer)

    command = service["command"]
    args = command if sys.platform == "win32" else shlex.split(command)
    process = subprocess.Popen(
        args,
        cwd=service.get("cwd"),
        env=service.get("env"),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=False,
        shell=sys.platform == "win32",
    )

    writer.write_meta("service_start", name=name, command=command, pid=process.pid)
    thread = threading.Thread(target=_pump_output, args=(process, writer, line_buffer), daemon=True)
    thread.start()

    state.save_service(name, pid=process.pid, log_path=str(writer.current_path))
    return process.pid


def stop(name: str, timeout: float = 5.0) -> bool:
    entry = state.get_service(name)
    if entry is None or not _is_alive(entry["pid"]):
        if entry is not None:
            state.remove_service(name)
        return False

    pid = entry["pid"]
    if sys.platform == "win32":
        subprocess.run(["taskkill", "/PID", str(pid)], capture_output=True)
    else:
        os.kill(pid, signal.SIGTERM)

    deadline = time.time() + timeout
    while time.time() < deadline and _is_alive(pid):
        time.sleep(0.2)

    if _is_alive(pid):
        if sys.platform == "win32":
            subprocess.run(["taskkill", "/PID", str(pid), "/F"], capture_output=True)
        else:
            os.kill(pid, signal.SIGKILL)
        deadline = time.time() + timeout
        while time.time() < deadline and _is_alive(pid):
            time.sleep(0.2)

    state.remove_service(name)
    return True


def is_running(name: str) -> bool:
    entry = state.get_service(name)
    return entry is not None and _is_alive(entry["pid"])


def status() -> List[dict]:
    services = config.load_config()["services"]
    results = []
    for service in services:
        name = service["name"]
        entry = state.get_service(name)
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
