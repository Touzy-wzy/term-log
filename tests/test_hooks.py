from termlog import hooks


def test_bash_snippet_guards_against_recursion():
    snippet = hooks.bash_snippet("/usr/bin/python3")
    assert "TERMLOG_SESSION" in snippet
    assert "termlog.recorder" in snippet


def test_bash_snippet_embeds_the_given_python_executable():
    snippet = hooks.bash_snippet("/usr/bin/python3")
    assert "/usr/bin/python3" in snippet


def test_bash_snippet_normalizes_windows_backslashes():
    snippet = hooks.bash_snippet("E:\\termlog\\.venv\\Scripts\\python.exe")
    assert "E:/termlog/.venv/Scripts/python.exe" in snippet
    assert "\\" not in snippet


def test_powershell_snippet_guards_against_recursion():
    snippet = hooks.powershell_snippet("C:\\Python\\python.exe")
    assert "TERMLOG_SESSION" in snippet
    assert "termlog.recorder" in snippet


def test_powershell_snippet_embeds_the_given_python_executable():
    snippet = hooks.powershell_snippet("C:\\Python\\python.exe")
    assert "C:\\Python\\python.exe" in snippet


def test_bash_snippet_only_recurses_for_interactive_shells():
    # Regression test: a non-interactive bash invocation (a script, or a
    # tool running `bash -c "..."`) reads .bashrc too, but must never be
    # handed to the recorder — the recorder waits on keyboard input that a
    # non-interactive caller can never provide, so it would hang forever.
    snippet = hooks.bash_snippet("/usr/bin/python3")
    assert '"$-"' in snippet
    assert "*i*" in snippet


def test_bash_snippet_does_not_invoke_recorder_when_sourced_non_interactively(tmp_path):
    import shutil
    import subprocess

    bash = shutil.which("bash")
    if bash is None:
        import pytest

        pytest.skip("bash not available on this machine")

    marker_file = tmp_path / "recorder_invoked.marker"
    # A fake "python" that just proves it was invoked, instead of actually
    # launching termlog.recorder (which would hang forever waiting on a PTY
    # that doesn't exist in this test).
    fake_python = tmp_path / "fake_python.sh"
    fake_python.write_text(f'#!/bin/sh\ntouch "{marker_file}"\n', encoding="utf-8")
    fake_python.chmod(0o755)

    rc_file = tmp_path / "fake_rc.sh"
    rc_file.write_text(hooks.bash_snippet(str(fake_python)), encoding="utf-8")

    # `bash -c "source ..."` is a NON-interactive invocation (no -i flag),
    # exactly like a script or a tool shelling out to bash. This must
    # complete quickly and must never touch the marker file.
    result = subprocess.run(
        [bash, "-c", f'source "{rc_file}"'],
        capture_output=True,
        timeout=10,
    )
    assert result.returncode == 0
    assert not marker_file.exists()


def test_powershell_snippet_only_recurses_when_user_interactive():
    snippet = hooks.powershell_snippet("C:\\Python\\python.exe")
    assert "[Environment]::UserInteractive" in snippet


def test_install_snippet_appends_when_file_empty(tmp_path):
    target = tmp_path / ".bashrc"
    target.write_text("", encoding="utf-8")
    changed = hooks.install_snippet(
        target, hooks.bash_snippet("/usr/bin/python3"), hooks.BASH_MARKER_START, hooks.BASH_MARKER_END
    )
    content = target.read_text(encoding="utf-8")
    assert changed is True
    assert hooks.BASH_MARKER_START in content
    assert hooks.BASH_MARKER_END in content


def test_install_snippet_preserves_existing_content(tmp_path):
    target = tmp_path / ".bashrc"
    target.write_text("export PATH=$PATH:/foo\n", encoding="utf-8")
    hooks.install_snippet(
        target, hooks.bash_snippet("/usr/bin/python3"), hooks.BASH_MARKER_START, hooks.BASH_MARKER_END
    )
    content = target.read_text(encoding="utf-8")
    assert "export PATH=$PATH:/foo" in content


def test_install_snippet_is_idempotent(tmp_path):
    target = tmp_path / ".bashrc"
    target.write_text("", encoding="utf-8")
    hooks.install_snippet(
        target, hooks.bash_snippet("/usr/bin/python3"), hooks.BASH_MARKER_START, hooks.BASH_MARKER_END
    )
    first_content = target.read_text(encoding="utf-8")
    changed_again = hooks.install_snippet(
        target, hooks.bash_snippet("/usr/bin/python3"), hooks.BASH_MARKER_START, hooks.BASH_MARKER_END
    )
    second_content = target.read_text(encoding="utf-8")
    assert changed_again is False
    assert first_content == second_content
    assert first_content.count(hooks.BASH_MARKER_START) == 1


def test_uninstall_snippet_removes_section(tmp_path):
    target = tmp_path / ".bashrc"
    target.write_text("export PATH=$PATH:/foo\n", encoding="utf-8")
    hooks.install_snippet(
        target, hooks.bash_snippet("/usr/bin/python3"), hooks.BASH_MARKER_START, hooks.BASH_MARKER_END
    )
    removed = hooks.uninstall_snippet(target, hooks.BASH_MARKER_START, hooks.BASH_MARKER_END)
    content = target.read_text(encoding="utf-8")
    assert removed is True
    assert hooks.BASH_MARKER_START not in content
    assert "export PATH=$PATH:/foo" in content


def test_uninstall_snippet_returns_false_when_absent(tmp_path):
    target = tmp_path / ".bashrc"
    target.write_text("export PATH=$PATH:/foo\n", encoding="utf-8")
    removed = hooks.uninstall_snippet(target, hooks.BASH_MARKER_START, hooks.BASH_MARKER_END)
    assert removed is False


def test_install_snippet_backs_up_original_file_once(tmp_path):
    target = tmp_path / ".bashrc"
    target.write_text("export PATH=$PATH:/foo\n", encoding="utf-8")
    hooks.install_snippet(
        target, hooks.bash_snippet("/usr/bin/python3"), hooks.BASH_MARKER_START, hooks.BASH_MARKER_END
    )
    backup = tmp_path / ".bashrc.termlog.bak"
    assert backup.exists()
    assert backup.read_text(encoding="utf-8") == "export PATH=$PATH:/foo\n"

    # A second install must not clobber the original backup with the
    # already-hooked content.
    hooks.install_snippet(
        target, hooks.bash_snippet("/usr/bin/python3"), hooks.BASH_MARKER_START, hooks.BASH_MARKER_END
    )
    assert backup.read_text(encoding="utf-8") == "export PATH=$PATH:/foo\n"


def test_install_snippet_does_not_back_up_nonexistent_file(tmp_path):
    target = tmp_path / ".bashrc"
    hooks.install_snippet(
        target, hooks.bash_snippet("/usr/bin/python3"), hooks.BASH_MARKER_START, hooks.BASH_MARKER_END
    )
    backup = tmp_path / ".bashrc.termlog.bak"
    assert not backup.exists()
