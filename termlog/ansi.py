from __future__ import annotations

import re

# OSC (Operating System Command) sequences: ESC ] ... terminated by BEL or
# ESC \. These set things like the terminal window title and can contain
# arbitrary text before their terminator, so they must be stripped whole
# before any other pattern, or their payload would leak into the output.
_OSC_PATTERN = re.compile(r"\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)")

# CSI (Control Sequence Introducer) sequences: ESC [ <params> <letter>.
# Covers cursor movement, colors/styles (SGR), screen clearing, and the
# private "?"-prefixed mode-toggle sequences (e.g. the VT-input-mode
# announcement that caused the keyboard-forwarding bug this module's
# feature was requested alongside).
_CSI_PATTERN = re.compile(r"\x1b\[[0-9;?]*[a-zA-Z]")

# A handful of two-byte escape sequences outside the CSI/OSC families
# (e.g. character-set selection, ESC ( B).
_SIMPLE_ESCAPE_PATTERN = re.compile(r"\x1b[()#][A-Za-z0-9]")

# Anything else starting with ESC that the patterns above didn't already
# consume — including a bare trailing ESC with no following byte, from a
# sequence truncated mid-write.
_LEFTOVER_ESCAPE_PATTERN = re.compile(r"\x1b.?")

# Non-printable control bytes with no place in a "clean text" view. \n and
# \t are excluded (kept as-is); \r is also kept, since it's structural
# (carriage-return-based progress bars) rather than noise to strip.
_CONTROL_CHAR_PATTERN = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def _apply_backspaces(text: str) -> str:
    # A backspace byte means "erase the character before me", not "remove
    # yourself and leave your neighbors untouched". Dropping \x08 without
    # this interpretation turns an edited command line (typo, then
    # backspace, then retype) into garbled text, e.g. "l\x08ls" naively
    # loses only the \x08 and reads as "lls" instead of "ls".
    result = []
    for ch in text:
        if ch == "\x08":
            if result:
                result.pop()
        else:
            result.append(ch)
    return "".join(result)


def strip_ansi(text: str) -> str:
    text = _OSC_PATTERN.sub("", text)
    text = _CSI_PATTERN.sub("", text)
    text = _SIMPLE_ESCAPE_PATTERN.sub("", text)
    text = _LEFTOVER_ESCAPE_PATTERN.sub("", text)
    text = _apply_backspaces(text)
    text = _CONTROL_CHAR_PATTERN.sub("", text)
    return text
