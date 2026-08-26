import sys
from pathlib import Path

from termlog import hooks


def _home() -> Path:
    return Path.home()


def _python_executable() -> str:
    # The interpreter running `termlog hook install` right now is guaranteed
    # to have termlog importable (it's running termlog's own code). Baking
    # its absolute path into the hook means every new shell invokes that
    # exact interpreter, instead of whatever "python" happens to resolve to
    # first on that shell's PATH — which may not have termlog installed at
    # all, and previously caused every new terminal to fail outright.
    return sys.executable


def _targets():
    home = _home()
    python_executable = _python_executable()
    return [
        {
            "shell": "bash",
            "path": home / ".bashrc",
            "snippet": hooks.bash_snippet(python_executable),
            "marker_start": hooks.BASH_MARKER_START,
            "marker_end": hooks.BASH_MARKER_END,
        },
        {
            "shell": "powershell",
            "path": home / "Documents" / "WindowsPowerShell" / "Microsoft.PowerShell_profile.ps1",
            "snippet": hooks.powershell_snippet(python_executable),
            "marker_start": hooks.POWERSHELL_MARKER_START,
            "marker_end": hooks.POWERSHELL_MARKER_END,
        },
        {
            "shell": "powershell7",
            "path": home / "Documents" / "PowerShell" / "Microsoft.PowerShell_profile.ps1",
            "snippet": hooks.powershell_snippet(python_executable),
            "marker_start": hooks.POWERSHELL_MARKER_START,
            "marker_end": hooks.POWERSHELL_MARKER_END,
        },
    ]


def discover_targets() -> list:
    return [
        {"shell": t["shell"], "path": t["path"], "exists": t["path"].exists()}
        for t in _targets()
    ]


def install_all() -> list:
    results = []
    for t in _targets():
        installed = hooks.install_snippet(t["path"], t["snippet"], t["marker_start"], t["marker_end"])
        results.append({"shell": t["shell"], "path": t["path"], "installed": installed})
    return results


def uninstall_all() -> list:
    results = []
    for t in _targets():
        removed = hooks.uninstall_snippet(t["path"], t["marker_start"], t["marker_end"])
        results.append({"shell": t["shell"], "path": t["path"], "removed": removed})
    return results


def status() -> list:
    results = []
    for t in _targets():
        present = False
        if t["path"].exists():
            content = t["path"].read_text(encoding="utf-8")
            present = t["marker_start"] in content and t["marker_end"] in content
        results.append({"shell": t["shell"], "path": t["path"], "hook_present": present})
    return results
