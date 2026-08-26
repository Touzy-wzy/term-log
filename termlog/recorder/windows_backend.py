import socket

from winpty import PtyProcess

from termlog.recorder.windows_console import RawInputMode
from termlog.storage import LineBuffer


def run(command: list, session) -> int:
    process = PtyProcess.spawn(command)
    # process.read() blocks on the underlying socket with no timeout, so a
    # child that stops producing output (but hasn't yet been reaped as dead)
    # can hang the loop forever. Give the socket a short timeout so read()
    # raises socket.timeout instead, letting the loop re-check isalive().
    process.fileobj.settimeout(0.05)
    line_buffer = LineBuffer(session.writer)

    # pywinpty relays child output to the socket via a background reader
    # thread, and that relay can lag slightly behind the pty reporting the
    # process as no-longer-alive. Bailing out on the very first
    # timeout-after-death risks dropping output that was already in
    # flight but hadn't reached the socket yet. Requiring several
    # consecutive empty-and-dead reads before giving up gives that relay
    # a real chance to catch up first.
    CONSECUTIVE_DEAD_READS_BEFORE_EXIT = 5

    try:
        with RawInputMode() as console_input:
            dead_streak = 0
            while True:
                # Forward any pending keystrokes first. This is a separate
                # check from the output read below — an earlier version
                # used `continue` on the output read's timeout, which
                # skipped straight back to the top of the loop and past
                # this check on almost every iteration (PowerShell spends
                # most of its time producing no output while it waits for
                # input), making keyboard forwarding effectively dead code.
                if console_input.has_input(timeout_ms=0):
                    typed = console_input.read()
                    if typed:
                        process.write(typed)

                try:
                    output = process.read(1024)
                except EOFError:
                    # The socket closed: the underlying pty and its reader
                    # thread are genuinely done, and there is nothing left
                    # to drain.
                    break
                except socket.timeout:
                    if process.isalive():
                        dead_streak = 0
                    else:
                        dead_streak += 1
                        if dead_streak >= CONSECUTIVE_DEAD_READS_BEFORE_EXIT:
                            break
                    continue

                dead_streak = 0
                if output:
                    encoded = output.encode("utf-8", errors="replace") if isinstance(output, str) else output
                    print(output, end="", flush=True)
                    line_buffer.feed(encoded)
    finally:
        line_buffer.flush()

    process.wait()
    return process.exitstatus or 0
