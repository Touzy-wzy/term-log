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

## Known limitations

- On Windows, arrow-key / extended-key forwarding in the recorder is
  best-effort (see `termlog/recorder/windows_backend.py`).
- Non-interactive or `--noprofile`/`-NoProfile` shell launches (e.g. some
  CI or IDE task runners) don't read the hooked startup files, so they
  won't be auto-recorded.
