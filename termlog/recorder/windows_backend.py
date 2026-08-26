import msvcrt
import socket
import time

from winpty import PtyProcess

from termlog.storage import LineBuffer


def run(command: list, session) -> int:
    process = PtyProcess.spawn(command)
    # process.read() blocks on the underlying socket with no timeout, so a
    # child that stops producing output (but hasn't yet been reaped as dead)
    # can hang the loop forever. Give the socket a short timeout so read()
    # raises socket.timeout instead, letting the loop re-check isalive().
    process.fileobj.settimeout(0.1)
    line_buffer = LineBuffer(session.writer)

    try:
        while process.isalive():
            try:
                output = process.read(1024)
            except EOFError:
                break
            except socket.timeout:
                continue
            if output:
                encoded = output.encode("utf-8", errors="replace") if isinstance(output, str) else output
                print(output, end="", flush=True)
                line_buffer.feed(encoded)

            if msvcrt.kbhit():
                key = msvcrt.getch()
                process.write(key.decode("utf-8", errors="replace"))

            time.sleep(0.01)
    finally:
        line_buffer.flush()

    process.wait()
    return process.exitstatus or 0
