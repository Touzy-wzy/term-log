import time

from termlog import paths, service_collector


def _write_config(tmp_path, services):
    tmp_path.mkdir(exist_ok=True)
    lines = ["services:"]
    for s in services:
        lines.append(f"  - name: {s['name']}")
        lines.append(f"    command: {s['command']}")
        lines.append(f"    cwd: {s['cwd']}")
    paths.config_path().write_text("\n".join(lines) + "\n", encoding="utf-8")


QUICK_CMD = "python -c \"print('collector-ran', flush=True)\""


def test_main_returns_1_for_unknown_service(tmp_path, monkeypatch):
    monkeypatch.setenv("TERMLOG_HOME", str(tmp_path))
    _write_config(tmp_path, [])
    exit_code = service_collector.main(["missing", "E:/proj", "missing.log"])
    assert exit_code == 1


def test_main_writes_output_and_exit_code_to_named_file(tmp_path, monkeypatch):
    monkeypatch.setenv("TERMLOG_HOME", str(tmp_path))
    _write_config(tmp_path, [{"name": "quick", "command": QUICK_CMD, "cwd": str(tmp_path)}])

    exit_code = service_collector.main(["quick", "E:/proj", "quick_fixed.log"])

    assert exit_code == 0
    log_path = paths.services_dir("E:/proj", "quick") / "quick_fixed.log"
    content = log_path.read_text(encoding="utf-8", errors="replace")
    assert "collector-ran" in content
    assert "service_start" in content
    assert "service_exit" in content
    assert "exit_code=0" in content
