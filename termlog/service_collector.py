from __future__ import annotations

import shlex
import subprocess
import sys

from termlog import config, paths
from termlog.storage import LineBuffer, LogWriter


def main(argv=None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    name, project_path, log_filename = argv[0], argv[1], argv[2]

    service = config.find_service(name)
    if service is None:
        return 1

    max_size_mb = config.load_config()["max_log_size_mb"]
    writer = LogWriter(
        paths.services_dir(project_path, name),
        prefix=name,
        max_size_mb=max_size_mb,
        initial_filename=log_filename,
    )
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

    if process.stdout is not None:
        for raw_line in process.stdout:
            line_buffer.feed(raw_line if isinstance(raw_line, bytes) else raw_line.encode("utf-8"))
    line_buffer.flush()

    exit_code = process.wait()
    writer.write_meta("service_exit", exit_code=exit_code)
    writer.close()
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
