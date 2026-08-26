# termlog

Automatic terminal session and service log capture for local development.

## Install

    cd E:/termlog
    python -m venv .venv
    source .venv/Scripts/activate   # or .venv/bin/activate on Linux/Mac
    pip install -e ".[windows]"     # omit [windows] on Linux/Mac

## Set up automatic session recording

    termlog hook install

This patches `~/.bashrc` and your PowerShell `$PROFILE` with a guarded
snippet. Every new terminal window you open afterward is automatically
wrapped in a recorder — you use it exactly as before, and everything
that appears in that terminal is also saved to
`~/.termlog/logs/<project>/sessions/`.

Check status any time with `termlog hook status`; remove with
`termlog hook uninstall`.

## Capture a long-running dev service

Add to `~/.termlog/termlog.yaml`:

    services:
      - name: my-api
        command: python app.py
        cwd: E:/my-project

Then:

    termlog service start my-api
    termlog service status
    termlog service logs my-api -f
    termlog service stop my-api

## Configuration

`~/.termlog/termlog.yaml`:

    retention_days: 14      # delete session/service logs older than this
    max_log_size_mb: 50     # rotate a log file once it exceeds this size

## Viewing a log as plain text

Captured logs preserve raw ANSI escape sequences (colors, cursor
movement) verbatim, so opening one directly in a plain text editor shows
a lot of `[?25l[93m...` noise mixed in with the real content. To view or
export a clean, human-readable version:

    termlog log view <path-to-log-file>
    termlog log view <path-to-log-file> --out <path-to-clean-file>

This does not change what gets written to the log file itself — only
what `log view` prints/exports.

## Known limitations

- Non-interactive shell invocations (scripts, tools running
  `bash -c "..."` or `powershell -Command "..."`, this recorder's own
  relaunched shell) are intentionally skipped by the hook — only real
  interactive terminal sessions are recorded. A non-interactive caller
  has no keyboard, so handing it to the recorder would hang forever
  waiting for input that will never arrive.
- Because the hook fully replaces the shell process it wraps, tools that
  auto-run a setup command against a terminal right after opening it
  (e.g. VS Code's automatic virtualenv activation on "New Terminal") can
  send that command to the pre-hook shell process, which has already
  handed off control to the recorder by the time the command arrives —
  the command is effectively lost. Terminal output is still fully
  captured in this case; only that one auto-injected setup command is
  affected. Re-run it manually (e.g. `.\.venv\Scripts\Activate.ps1`) if
  this happens.
