import socket
import time

from winpty import PtyProcess

from termlog.recorder.windows_console import RawInputMode, get_console_dimensions
from termlog.storage import LineBuffer

# How often to re-check the real console's size against what the captured
# child shell currently thinks it is. The captured shell computes cursor
# positions for redraws (arrow-key history recall, tab completion) against
# whatever size it was last told — if the user resizes the terminal window
# mid-session and this never gets checked again, redraws go right back to
# being garbled/misplaced, just like the original fixed-80x24 bug this
# polling closes the other half of. A half-second interval is frequent
# enough that a resize is picked up quickly without meaningfully adding to
# this loop's per-iteration cost.
RESIZE_CHECK_INTERVAL_SECONDS = 0.5


def run(command: list, session) -> int:
    # PtyProcess.spawn defaults to a fixed 80x24 pty when no dimensions
    # are given, regardless of the real console's actual size. The
    # captured child shell then computes cursor positions for things like
    # arrow-key history redraw or tab completion against that wrong size,
    # producing garbled/misplaced output whenever the real window is a
    # different size (almost always, since 80x24 is rarely anyone's
    # actual terminal size).
    current_dimensions = get_console_dimensions()
    process = PtyProcess.spawn(command, dimensions=current_dimensions)
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
            next_resize_check = time.monotonic() + RESIZE_CHECK_INTERVAL_SECONDS
            while True:
                now = time.monotonic()
                if now >= next_resize_check:
                    next_resize_check = now + RESIZE_CHECK_INTERVAL_SECONDS
                    latest_dimensions = get_console_dimensions()
                    if latest_dimensions != current_dimensions:
                        current_dimensions = latest_dimensions
                        rows, cols = current_dimensions
                        process.setwinsize(rows, cols)

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
