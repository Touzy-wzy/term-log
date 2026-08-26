import os
import sys

if sys.platform != "win32":
    import pty
    import select

from termlog.storage import LineBuffer


def run(command: list, session) -> int:
    pid, master_fd = pty.fork()

    if pid == 0:
        os.execvp(command[0], command)
        os._exit(1)

    line_buffer = LineBuffer(session.writer)
    child_done = False
    status = 0
    try:
        while True:
            try:
                readable, _, _ = select.select([master_fd, sys.stdin.fileno()], [], [], 0.1)
            except InterruptedError:
                continue

            if sys.stdin.fileno() in readable:
                try:
                    user_input = os.read(sys.stdin.fileno(), 1024)
                except OSError:
                    user_input = b""
                if user_input:
                    os.write(master_fd, user_input)

            if master_fd in readable:
                try:
                    output = os.read(master_fd, 1024)
                except OSError:
                    output = b""
                if output:
                    os.write(sys.stdout.fileno(), output)
                    line_buffer.feed(output)
                else:
                    break

            reaped_pid, status = os.waitpid(pid, os.WNOHANG)
            if reaped_pid != 0:
                child_done = True
                break
    finally:
        line_buffer.flush()
        os.close(master_fd)

    if not child_done:
        _, status = os.waitpid(pid, 0)
    if os.WIFEXITED(status):
        return os.WEXITSTATUS(status)
    return 1
