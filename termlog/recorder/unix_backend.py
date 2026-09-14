import os
import signal
import struct
import sys

if sys.platform != "win32":
    import fcntl
    import pty
    import select
    import termios

from termlog.storage import LineBuffer


def _sync_pty_size(master_fd):
    try:
        cols, rows = os.get_terminal_size(sys.stdin.fileno())
    except OSError:
        return
    winsize = struct.pack("HHHH", rows, cols, 0, 0)
    fcntl.ioctl(master_fd, termios.TIOCSWINSZ, winsize)


def run(command: list, session) -> int:
    pid, master_fd = pty.fork()

    if pid == 0:
        os.execvp(command[0], command)
        os._exit(1)

    # pty.fork() doesn't size the new pty to match the real terminal, so the
    # captured child shell starts out computing cursor positions (arrow-key
    # history redraw, tab completion) against the wrong size until it's
    # first resized. Sync it up front, then keep it in sync via SIGWINCH so
    # a real window resize during the session propagates to the child too.
    _sync_pty_size(master_fd)

    def _on_sigwinch(signum, frame):
        # Setting TIOCSWINSZ on the master is enough: the kernel delivers
        # SIGWINCH to the slave side's foreground process group itself when
        # the size actually changes, so the child shell picks it up without
        # us signaling it directly.
        _sync_pty_size(master_fd)

    previous_handler = signal.signal(signal.SIGWINCH, _on_sigwinch)

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
        signal.signal(signal.SIGWINCH, previous_handler)
        line_buffer.flush()
        os.close(master_fd)

    if not child_done:
        _, status = os.waitpid(pid, 0)
    if os.WIFEXITED(status):
        return os.WEXITSTATUS(status)
    return 1
