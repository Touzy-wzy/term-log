from __future__ import annotations

import ctypes
from ctypes import wintypes

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

STD_INPUT_HANDLE = -10
INVALID_HANDLE_VALUE = -1
WAIT_OBJECT_0 = 0x00000000
WAIT_TIMEOUT = 0x00000102
WAIT_FAILED = 0xFFFFFFFF

# Console input mode flags (see Microsoft's SetConsoleMode documentation).
ENABLE_PROCESSED_INPUT = 0x0001
ENABLE_LINE_INPUT = 0x0002
ENABLE_ECHO_INPUT = 0x0004
ENABLE_VIRTUAL_TERMINAL_INPUT = 0x0200

# The mode this module puts the console into while forwarding keystrokes
# to a captured child shell:
#   - ENABLE_VIRTUAL_TERMINAL_INPUT: special keys (arrows, function keys,
#     etc) arrive as standard ANSI escape sequences mixed into the same
#     character stream as normal typing, instead of via a separate
#     structured "virtual key" mechanism. This lets the recorder forward
#     everything as opaque bytes/characters, exactly like the Unix PTY
#     backend already does, without needing to decode or interpret any
#     individual key.
#   - ENABLE_LINE_INPUT is intentionally NOT set: without it, ReadConsoleW
#     returns whatever has been typed so far without waiting for Enter,
#     so keystrokes reach the child shell as you type them rather than
#     only after a full line is buffered.
#   - ENABLE_ECHO_INPUT is intentionally NOT set: the console would
#     otherwise print what you type itself. The child shell already
#     echoes its own input as part of its normal output, and that output
#     is already being captured and printed by the backend's separate
#     output-forwarding loop — a second, local echo would show every
#     keystroke twice.
#   - ENABLE_PROCESSED_INPUT is intentionally NOT set: with it on, the
#     console intercepts Ctrl+C itself (as a signal to this process)
#     instead of delivering it as the raw byte 0x03. Forwarding raw bytes
#     is what lets Ctrl+C reach the captured child shell as input,
#     matching how it behaves in an uncaptured terminal.
RAW_FORWARDING_MODE = ENABLE_VIRTUAL_TERMINAL_INPUT

kernel32.GetStdHandle.restype = wintypes.HANDLE
kernel32.GetStdHandle.argtypes = [wintypes.DWORD]

kernel32.GetConsoleMode.restype = wintypes.BOOL
kernel32.GetConsoleMode.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]

kernel32.SetConsoleMode.restype = wintypes.BOOL
kernel32.SetConsoleMode.argtypes = [wintypes.HANDLE, wintypes.DWORD]

kernel32.WaitForSingleObject.restype = wintypes.DWORD
kernel32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]

kernel32.ReadConsoleW.restype = wintypes.BOOL
kernel32.ReadConsoleW.argtypes = [
    wintypes.HANDLE,
    wintypes.LPVOID,
    wintypes.DWORD,
    ctypes.POINTER(wintypes.DWORD),
    wintypes.LPVOID,
]


class RawInputMode:
    """Context manager that puts the real console stdin into raw,
    VT-input-forwarding mode for the duration of a captured shell session,
    and always restores the original mode afterward.

    If there is no real console attached to this process (or the mode
    change otherwise fails — e.g. when running under a test harness or a
    non-console environment), `active` is False and no console state is
    touched. Callers must check `active` before using `has_input`/`read`;
    with `active` False, keyboard forwarding is simply skipped rather than
    the whole recorder crashing.
    """

    def __init__(self):
        self.handle = None
        self.original_mode = None
        self.active = False

    def __enter__(self) -> "RawInputMode":
        handle = kernel32.GetStdHandle(STD_INPUT_HANDLE)
        if not handle or handle == INVALID_HANDLE_VALUE:
            return self

        current_mode = wintypes.DWORD()
        if not kernel32.GetConsoleMode(handle, ctypes.byref(current_mode)):
            return self

        if not kernel32.SetConsoleMode(handle, wintypes.DWORD(RAW_FORWARDING_MODE)):
            return self

        self.handle = handle
        self.original_mode = current_mode.value
        self.active = True
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        if self.active and self.handle is not None and self.original_mode is not None:
            kernel32.SetConsoleMode(self.handle, wintypes.DWORD(self.original_mode))

    def has_input(self, timeout_ms: int = 0) -> bool:
        if not self.active:
            return False
        result = kernel32.WaitForSingleObject(self.handle, wintypes.DWORD(timeout_ms))
        return result == WAIT_OBJECT_0

    def read(self, max_chars: int = 1024) -> str:
        if not self.active:
            return ""
        buffer = ctypes.create_unicode_buffer(max_chars)
        chars_read = wintypes.DWORD()
        ok = kernel32.ReadConsoleW(
            self.handle,
            buffer,
            wintypes.DWORD(max_chars),
            ctypes.byref(chars_read),
            None,
        )
        if not ok:
            return ""
        return buffer[: chars_read.value]
