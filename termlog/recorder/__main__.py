import os
import sys

from termlog.recorder.session import RecordedSession, detect_shell

SHELL_COMMANDS = {
    "bash": ["bash"],
    "zsh": ["zsh"],
    "powershell": ["powershell", "-NoLogo"],
}


def main() -> int:
    shell_name = detect_shell()
    command = SHELL_COMMANDS.get(shell_name, ["bash"])

    session = RecordedSession(os.getcwd())
    session.start(shell_name=shell_name)

    if sys.platform == "win32":
        from termlog.recorder import windows_backend

        exit_code = windows_backend.run(command, session)
    else:
        from termlog.recorder import unix_backend

        exit_code = unix_backend.run(command, session)

    session.end(exit_code=exit_code)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
