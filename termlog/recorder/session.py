import os
import sys

from termlog import paths, state
from termlog.storage import LogWriter


def detect_shell() -> str:
    shell_env = os.environ.get("SHELL", "")
    if "zsh" in shell_env:
        return "zsh"
    if "bash" in shell_env:
        return "bash"
    if os.environ.get("PSModulePath"):
        return "powershell"
    if sys.platform == "win32":
        return "powershell"
    return "bash"


class RecordedSession:
    def __init__(self, project_path: str):
        self.project_path = project_path
        self.writer = LogWriter(
            paths.sessions_dir(project_path),
            prefix="session",
            max_size_mb=_max_log_size_mb(),
        )

    def start(self, shell_name: str) -> None:
        self.writer.write_meta("session_start", project=self.project_path, shell=shell_name)
        state.save_active_session(
            pid=os.getpid(),
            log_path=str(self.writer.current_path),
            project_path=self.project_path,
        )

    def end(self, exit_code: int) -> None:
        self.writer.write_meta("session_end", exit_code=exit_code)
        self.writer.close()
        state.remove_active_session(pid=os.getpid())


def _max_log_size_mb() -> int:
    from termlog import config

    return config.load_config()["max_log_size_mb"]
