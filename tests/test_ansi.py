from termlog.ansi import strip_ansi


def test_strips_sgr_color_codes():
    assert strip_ansi("\x1b[93mhello\x1b[m") == "hello"


def test_strips_cursor_and_screen_control_sequences():
    assert strip_ansi("\x1b[?25l\x1b[2J\x1b[m\x1b[Hhello") == "hello"


def test_strips_private_mode_toggle_sequences():
    # The exact VT-input-mode announcement that caused the keyboard-
    # forwarding bug this feature was requested alongside.
    assert strip_ansi("\x1b[?9001h\x1b[?1004h\x1b[?2004hhello") == "hello"


def test_strips_osc_window_title_sequences_bel_terminated():
    assert (
        strip_ansi("before\x1b]0;C:\\WINDOWS\\System32\\powershell.EXE\x07after")
        == "beforeafter"
    )


def test_strips_osc_sequences_esc_backslash_terminated():
    assert strip_ansi("before\x1b]0;title\x1b\\after") == "beforeafter"


def test_preserves_plain_text_and_newlines():
    assert strip_ansi("line one\nline two\n") == "line one\nline two\n"


def test_preserves_carriage_returns():
    # Carriage-return-based progress bars are structural content, not
    # terminal-control noise — stripping them would collapse a progress
    # bar's distinct updates into one unreadable line.
    assert strip_ansi("50%\r100%\r") == "50%\r100%\r"


def test_strips_trailing_truncated_escape_sequence():
    # A write that got cut off mid-sequence (e.g. log rotation landing
    # between an ESC byte and its follow-up) must not leave a stray ESC
    # byte or partial sequence in the output.
    assert strip_ansi("hello\x1b") == "hello"
    assert strip_ansi("hello\x1b[") == "hello"


def test_backspace_erases_preceding_character():
    # \x08 means "delete the character before me" (how a terminal renders
    # a retyped command line), not "delete yourself and leave neighbors
    # alone" — the bell (\x07) is still dropped as inaudible noise.
    assert strip_ansi("a\x08b\x07c") == "bc"


def test_backspace_with_nothing_before_it_is_a_no_op():
    assert strip_ansi("\x08abc") == "abc"


def test_retyped_command_reduces_to_final_text():
    # Drawn from a real captured session: the user typed "l", backspaced,
    # then typed "ls". Naive control-byte stripping used to render this as
    # "lls" instead of the command that was actually run.
    assert strip_ansi("l\x08ls") == "ls"


def test_real_captured_terminal_output_becomes_clean_text():
    # Drawn directly from an actual termlog session log captured during
    # manual verification (a PowerShell prompt with tab-completion state
    # updates), to confirm the combination of escape sequences produced by
    # real terminal usage — not just synthetic single-sequence cases —
    # reduces to genuinely readable text.
    raw = (
        "[?25l[93mpython[?25h[m"
        "[?25l[93m[2;18Hpython [?25h[m"
        "[?25l[93m[2;18Hpython [37mrun.py [?25h[m"
    )
    # Reconstruct with real ESC bytes (the literal brackets above stand in
    # for readability in this comment; the actual test uses \x1b).
    raw = raw.replace("[", "\x1b[")
    cleaned = strip_ansi(raw)
    assert "python" in cleaned
    assert "run.py" in cleaned
    assert "\x1b" not in cleaned


def test_multiline_captured_session_is_fully_readable():
    raw = (
        "\x1b[?25l\x1b[2J\x1b[m\x1b[HPS E:\\proj>\x1b]0;powershell.EXE\x07\n"
        "Traceback (most recent call last):\n"
        "  File \"run.py\", line 31, in <module>\n"
        "ModuleNotFoundError: No module named 'dotenv'\n"
    )
    cleaned = strip_ansi(raw)
    assert "\x1b" not in cleaned
    assert "PS E:\\proj>" in cleaned
    assert "Traceback (most recent call last):" in cleaned
    assert "ModuleNotFoundError: No module named 'dotenv'" in cleaned
