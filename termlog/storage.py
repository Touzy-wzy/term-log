import os
import time
from datetime import datetime
from pathlib import Path


class LogWriter:
    _sequence = 0

    def __init__(self, directory: Path, prefix: str, max_size_mb: int):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.prefix = prefix
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.current_path = self._new_path()
        self._fh = open(self.current_path, "a", encoding="utf-8", newline="")

    def _new_path(self) -> Path:
        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        pid = os.getpid()
        LogWriter._sequence += 1
        name = f"{self.prefix}_{timestamp}_pid{pid}_{LogWriter._sequence}.log"
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
