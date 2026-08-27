import sys
from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="Windows console API only")

from termlog.recorder.windows_console import (
    DEFAULT_DIMENSIONS,
    ENABLE_ECHO_INPUT,
    ENABLE_LINE_INPUT,
    ENABLE_PROCESSED_INPUT,
    ENABLE_VIRTUAL_TERMINAL_INPUT,
    RAW_FORWARDING_MODE,
    WAIT_OBJECT_0,
    RawInputMode,
    get_console_dimensions,
)


def test_raw_forwarding_mode_enables_vt_input_only():
    # VT input must be on (so arrows/special keys arrive as plain escape
    # sequences we can forward opaquely, like the Unix backend already
    # does) — but line/echo/processed-input must all stay off, or typed
    # keys wouldn't reach the child until Enter, would echo twice (once
    # locally, once via the child shell's own echo), or Ctrl+C would be
    # intercepted by this process instead of forwarded as raw input.
    assert RAW_FORWARDING_MODE & ENABLE_VIRTUAL_TERMINAL_INPUT
    assert not (RAW_FORWARDING_MODE & ENABLE_LINE_INPUT)
    assert not (RAW_FORWARDING_MODE & ENABLE_ECHO_INPUT)
    assert not (RAW_FORWARDING_MODE & ENABLE_PROCESSED_INPUT)


def test_degrades_gracefully_when_get_std_handle_fails():
    with patch("termlog.recorder.windows_console.kernel32") as mock_kernel32:
        mock_kernel32.GetStdHandle.return_value = 0
        with RawInputMode() as console_input:
            assert console_input.active is False
            assert console_input.has_input() is False
            assert console_input.read() == ""


def test_degrades_gracefully_when_get_console_mode_fails():
    with patch("termlog.recorder.windows_console.kernel32") as mock_kernel32:
        mock_kernel32.GetStdHandle.return_value = 123
        mock_kernel32.GetConsoleMode.return_value = False
        with RawInputMode() as console_input:
            assert console_input.active is False


def test_degrades_gracefully_when_set_console_mode_fails():
    with patch("termlog.recorder.windows_console.kernel32") as mock_kernel32:
        mock_kernel32.GetStdHandle.return_value = 123
        mock_kernel32.GetConsoleMode.return_value = True
        mock_kernel32.SetConsoleMode.return_value = False
        with RawInputMode() as console_input:
            assert console_input.active is False


def test_activates_and_restores_original_mode_on_exit():
    with patch("termlog.recorder.windows_console.kernel32") as mock_kernel32:
        mock_kernel32.GetStdHandle.return_value = 123
        mock_kernel32.GetConsoleMode.return_value = True

        original_mode_holder = {}

        def fake_get_console_mode(handle, out_ptr):
            out_ptr._obj.value = 0x0003  # arbitrary "original" mode bits
            original_mode_holder["value"] = 0x0003
            return True

        mock_kernel32.GetConsoleMode.side_effect = fake_get_console_mode
        mock_kernel32.SetConsoleMode.return_value = True

        with RawInputMode() as console_input:
            assert console_input.active is True
            set_call_args = mock_kernel32.SetConsoleMode.call_args_list[0]
            assert set_call_args[0][1].value == RAW_FORWARDING_MODE

        # On exit, SetConsoleMode must be called a second time to restore
        # the mode the console was in before this context manager touched it.
        restore_call_args = mock_kernel32.SetConsoleMode.call_args_list[1]
        assert restore_call_args[0][1].value == original_mode_holder["value"]


def test_has_input_returns_false_when_inactive():
    console_input = RawInputMode()
    assert console_input.active is False
    assert console_input.has_input() is False


def test_read_returns_empty_string_when_inactive():
    console_input = RawInputMode()
    assert console_input.read() == ""


def test_has_input_reflects_wait_result():
    with patch("termlog.recorder.windows_console.kernel32") as mock_kernel32:
        mock_kernel32.GetStdHandle.return_value = 123
        mock_kernel32.GetConsoleMode.return_value = True
        mock_kernel32.SetConsoleMode.return_value = True
        mock_kernel32.WaitForSingleObject.return_value = WAIT_OBJECT_0

        with RawInputMode() as console_input:
            assert console_input.has_input(timeout_ms=0) is True
            mock_kernel32.WaitForSingleObject.return_value = 0x00000102  # WAIT_TIMEOUT
            assert console_input.has_input(timeout_ms=0) is False


def test_read_decodes_the_console_buffer_up_to_chars_read():
    with patch("termlog.recorder.windows_console.kernel32") as mock_kernel32:
        mock_kernel32.GetStdHandle.return_value = 123
        mock_kernel32.GetConsoleMode.return_value = True
        mock_kernel32.SetConsoleMode.return_value = True

        def fake_read_console(handle, buffer, max_chars, chars_read_ptr, reserved):
            text = "ab"
            for i, c in enumerate(text):
                buffer[i] = c
            chars_read_ptr._obj.value = len(text)
            return True

        mock_kernel32.ReadConsoleW.side_effect = fake_read_console

        with RawInputMode() as console_input:
            assert console_input.read(max_chars=10) == "ab"


def test_get_console_dimensions_falls_back_when_get_std_handle_fails():
    # Regression test: the root cause of arrow-key/tab-completion redraw
    # corruption — PtyProcess.spawn() defaulted to a fixed 80x24 pty
    # regardless of the real console's actual size, so the captured child
    # shell computed cursor positions against the wrong dimensions. This
    # confirms the fallback used when there's no real console at all
    # (e.g. under this test harness) matches pywinpty's own (24, 80)
    # default rather than returning something nonsensical.
    with patch("termlog.recorder.windows_console.kernel32") as mock_kernel32:
        mock_kernel32.GetStdHandle.return_value = 0
        assert get_console_dimensions() == DEFAULT_DIMENSIONS


def test_get_console_dimensions_falls_back_when_buffer_info_query_fails():
    with patch("termlog.recorder.windows_console.kernel32") as mock_kernel32:
        mock_kernel32.GetStdHandle.return_value = 123
        mock_kernel32.GetConsoleScreenBufferInfo.return_value = False
        assert get_console_dimensions() == DEFAULT_DIMENSIONS


def test_get_console_dimensions_returns_rows_cols_from_window_rect():
    with patch("termlog.recorder.windows_console.kernel32") as mock_kernel32:
        mock_kernel32.GetStdHandle.return_value = 123

        def fake_get_buffer_info(handle, info_ptr):
            info_ptr._obj.srWindow.Left = 0
            info_ptr._obj.srWindow.Right = 119  # 120 columns (0-indexed inclusive)
            info_ptr._obj.srWindow.Top = 0
            info_ptr._obj.srWindow.Bottom = 29  # 30 rows
            return True

        mock_kernel32.GetConsoleScreenBufferInfo.side_effect = fake_get_buffer_info
        assert get_console_dimensions() == (30, 120)


def test_get_console_dimensions_falls_back_on_degenerate_size():
    with patch("termlog.recorder.windows_console.kernel32") as mock_kernel32:
        mock_kernel32.GetStdHandle.return_value = 123

        def fake_get_buffer_info(handle, info_ptr):
            info_ptr._obj.srWindow.Left = 0
            info_ptr._obj.srWindow.Right = -1  # 0 columns — degenerate
            info_ptr._obj.srWindow.Top = 0
            info_ptr._obj.srWindow.Bottom = 29
            return True

        mock_kernel32.GetConsoleScreenBufferInfo.side_effect = fake_get_buffer_info
        assert get_console_dimensions() == DEFAULT_DIMENSIONS
