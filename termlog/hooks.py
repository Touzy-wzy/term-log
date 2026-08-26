from pathlib import Path

BASH_MARKER_START = "# >>> termlog hook >>>"
BASH_MARKER_END = "# <<< termlog hook <<<"
POWERSHELL_MARKER_START = "# >>> termlog hook >>>"
POWERSHELL_MARKER_END = "# <<< termlog hook <<<"


def bash_snippet() -> str:
    return (
        f"{BASH_MARKER_START}\n"
        'if [ -z "$TERMLOG_SESSION" ]; then\n'
        '  export TERMLOG_SESSION=1\n'
        '  exec python -m termlog.recorder\n'
        "fi\n"
        f"{BASH_MARKER_END}\n"
    )


def powershell_snippet() -> str:
    return (
        f"{POWERSHELL_MARKER_START}\n"
        'if (-not $env:TERMLOG_SESSION) {\n'
        '    $env:TERMLOG_SESSION = "1"\n'
        "    python -m termlog.recorder\n"
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
