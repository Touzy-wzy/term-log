from pathlib import Path

BASH_MARKER_START = "# >>> termlog hook >>>"
BASH_MARKER_END = "# <<< termlog hook <<<"
POWERSHELL_MARKER_START = "# >>> termlog hook >>>"
POWERSHELL_MARKER_END = "# <<< termlog hook <<<"


def bash_snippet(python_executable: str) -> str:
    # Bash treats backslashes specially even inside double quotes, so a raw
    # Windows path (e.g. "E:\termlog\.venv\Scripts\python.exe") would be
    # mangled. Windows accepts forward slashes in paths just as well, so
    # normalize to avoid that without needing extra escaping.
    python_path = python_executable.replace("\\", "/")
    return (
        f"{BASH_MARKER_START}\n"
        # `$-` lists the shell's active option flags; bash includes "i" in
        # it only for an interactive shell. Non-interactive invocations
        # (scripts, tools running `bash -c "..."`, this recorder's own
        # relaunched shell) never get "i". The recording logic is nested
        # inside this case branch (rather than guarded by an early
        # return/exit) so a non-interactive shell that sources .bashrc as
        # part of its own setup — then keeps running more commands — is
        # never short-circuited; it just skips straight past this block.
        'case "$-" in\n'
        "  *i*)\n"
        '    if [ -z "$TERMLOG_SESSION" ]; then\n'
        '      export TERMLOG_SESSION=1\n'
        f'      exec "{python_path}" -m termlog.recorder\n'
        "    fi\n"
        "    ;;\n"
        "esac\n"
        f"{BASH_MARKER_END}\n"
    )


def powershell_snippet(python_executable: str) -> str:
    return (
        f"{POWERSHELL_MARKER_START}\n"
        # [Environment]::UserInteractive is false for non-interactive
        # invocations (scripts, tools running powershell -Command "...",
        # this recorder's own relaunched shell). Skipping those avoids
        # handing them to a recorder that would block forever waiting for
        # keyboard input nobody is going to provide.
        "if ([Environment]::UserInteractive -and (-not $env:TERMLOG_SESSION)) {\n"
        '    $env:TERMLOG_SESSION = "1"\n'
        f'    & "{python_executable}" -m termlog.recorder\n'
        "    exit $LASTEXITCODE\n"
        "}\n"
        f"{POWERSHELL_MARKER_END}\n"
    )


def _backup_path(target_file: Path) -> Path:
    return target_file.with_name(target_file.name + ".termlog.bak")


def install_snippet(target_file: Path, snippet: str, marker_start: str, marker_end: str) -> bool:
    target_file = Path(target_file)
    existing = target_file.read_text(encoding="utf-8") if target_file.exists() else ""

    if target_file.exists():
        backup = _backup_path(target_file)
        if not backup.exists():
            backup.write_text(existing, encoding="utf-8")

    if marker_start in existing and marker_end in existing:
        before, _, rest = existing.partition(marker_start)
        _, _, after = rest.partition(marker_end)
        current_block = marker_start + rest.split(marker_end)[0] + marker_end + "\n"
        if current_block.strip() == snippet.strip():
            return False
        new_content = before + snippet + after
        target_file.write_text(new_content, encoding="utf-8")
        return True

    target_file.parent.mkdir(parents=True, exist_ok=True)
    separator = "\n" if existing and not existing.endswith("\n") else ""
    new_content = existing + separator + snippet
    target_file.write_text(new_content, encoding="utf-8")
    return True


def uninstall_snippet(target_file: Path, marker_start: str, marker_end: str) -> bool:
    target_file = Path(target_file)
    if not target_file.exists():
        return False
    existing = target_file.read_text(encoding="utf-8")
    if marker_start not in existing or marker_end not in existing:
        return False
    before, _, rest = existing.partition(marker_start)
    _, _, after = rest.partition(marker_end)
    after = after.lstrip("\n")
    target_file.write_text(before + after, encoding="utf-8")
    return True
