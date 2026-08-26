import os
from datetime import datetime
from pathlib import Path


class LogWriter:
    def __init__(self, directory: Path, prefix: str, max_size_mb: int):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.prefix = prefix
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self._sequence = 0
        self.current_path = self._new_path()
        self._fh = open(self.current_path, "a", encoding="utf-8", newline="")

    def _new_path(self) -> Path:
        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S.%f")[:-3]
        pid = os.getpid()
        self._sequence += 1
        name = f"{self.prefix}_{timestamp}_pid{pid}_{self._sequence}.log"
        return self.directory / name

    def _rotate_if_needed(self, incoming_bytes: int) -> None:
        if self.current_path.stat().st_size + incoming_bytes > self.max_size_bytes:
            self._fh.close()
            self.current_path = self._new_path()
            self._fh = open(self.current_path, "a", encoding="utf-8", newline="")

    def write_line(self, text: str) -> None:
        stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        line = f"[{stamp}] {text}\n"
        encoded_len = len(line.encode("utf-8"))
        self._rotate_if_needed(encoded_len)
        self._fh.write(line)
        self._fh.flush()

    def write_meta(self, event: str, **fields) -> None:
        pairs = " ".join(f"{k}={v}" for k, v in fields.items())
        self.write_line(f"### {event} {pairs}".rstrip())

    def close(self) -> None:
        if not self._fh.closed:
            self._fh.close()


class LineBuffer:
    def __init__(self, writer: "LogWriter"):
        self.writer = writer
        self._buffer = b""

    def feed(self, data: bytes) -> None:
        self._buffer += data
        while b"\n" in self._buffer:
            line, self._buffer = self._buffer.split(b"\n", 1)
            self.writer.write_line(line.decode("utf-8", errors="replace"))

    def flush(self) -> None:
        if self._buffer:
            self.writer.write_line(self._buffer.decode("utf-8", errors="replace"))
            self._buffer = b""
