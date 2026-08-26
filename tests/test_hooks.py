from termlog import hooks


def test_bash_snippet_guards_against_recursion():
    snippet = hooks.bash_snippet()
    assert "TERMLOG_SESSION" in snippet
    assert "termlog.recorder" in snippet


def test_powershell_snippet_guards_against_recursion():
    snippet = hooks.powershell_snippet()
    assert "TERMLOG_SESSION" in snippet
    assert "termlog.recorder" in snippet


def test_install_snippet_appends_when_file_empty(tmp_path):
    target = tmp_path / ".bashrc"
    target.write_text("", encoding="utf-8")
    changed = hooks.install_snippet(
        target, hooks.bash_snippet(), hooks.BASH_MARKER_START, hooks.BASH_MARKER_END
    )
    content = target.read_text(encoding="utf-8")
    assert changed is True
    assert hooks.BASH_MARKER_START in content
    assert hooks.BASH_MARKER_END in content


def test_install_snippet_preserves_existing_content(tmp_path):
    target = tmp_path / ".bashrc"
    target.write_text("export PATH=$PATH:/foo\n", encoding="utf-8")
    hooks.install_snippet(
        target, hooks.bash_snippet(), hooks.BASH_MARKER_START, hooks.BASH_MARKER_END
    )
    content = target.read_text(encoding="utf-8")
    assert "export PATH=$PATH:/foo" in content


def test_install_snippet_is_idempotent(tmp_path):
    target = tmp_path / ".bashrc"
    target.write_text("", encoding="utf-8")
    hooks.install_snippet(
        target, hooks.bash_snippet(), hooks.BASH_MARKER_START, hooks.BASH_MARKER_END
    )
    first_content = target.read_text(encoding="utf-8")
    changed_again = hooks.install_snippet(
        target, hooks.bash_snippet(), hooks.BASH_MARKER_START, hooks.BASH_MARKER_END
    )
    second_content = target.read_text(encoding="utf-8")
    assert changed_again is False
    assert first_content == second_content
    assert first_content.count(hooks.BASH_MARKER_START) == 1


def test_uninstall_snippet_removes_section(tmp_path):
    target = tmp_path / ".bashrc"
    target.write_text("export PATH=$PATH:/foo\n", encoding="utf-8")
    hooks.install_snippet(
        target, hooks.bash_snippet(), hooks.BASH_MARKER_START, hooks.BASH_MARKER_END
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
        target, hooks.bash_snippet(), hooks.BASH_MARKER_START, hooks.BASH_MARKER_END
    )
    backup = tmp_path / ".bashrc.termlog.bak"
    assert backup.exists()
    assert backup.read_text(encoding="utf-8") == "export PATH=$PATH:/foo\n"

    # A second install must not clobber the original backup with the
    # already-hooked content.
    hooks.install_snippet(
        target, hooks.bash_snippet(), hooks.BASH_MARKER_START, hooks.BASH_MARKER_END
    )
    assert backup.read_text(encoding="utf-8") == "export PATH=$PATH:/foo\n"


def test_install_snippet_does_not_back_up_nonexistent_file(tmp_path):
    target = tmp_path / ".bashrc"
    hooks.install_snippet(
        target, hooks.bash_snippet(), hooks.BASH_MARKER_START, hooks.BASH_MARKER_END
    )
    backup = tmp_path / ".bashrc.termlog.bak"
    assert not backup.exists()
