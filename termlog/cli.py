import argparse
import json
import os
import sys
import time

from termlog import ansi, cleanup, config, hook_targets, log_export, service_manager, state

HOOK_STATUS_LIMITATIONS = [
    "只影响之后新打开的终端，不影响当前已经在用的这个终端/会话",
    "只有交互式 shell 会被记录；脚本、bash -c/-Command 之类的非交互调用会被跳过",
    "原样记录键盘输入的所有字节，包括密码等敏感信息，不做任何过滤或脱敏",
    "开启后持续生效，直到主动执行 uninstall，不是单次会话级别的开关",
]


def _cmd_hook_install(args) -> int:
    for result in hook_targets.install_all():
        status_text = "installed" if result["installed"] else "already up to date"
        print(f"{result['shell']}: {status_text} ({result['path']})")
    print(
        "note: only affects new terminals opened from now on; captures all keystrokes "
        "including passwords with no redaction"
    )
    return 0


def _cmd_hook_uninstall(args) -> int:
    exported = log_export.export_session_logs()
    if exported:
        print(f"exported {len(exported)} plain-text log(s) to sessions_view/services_view")
    for result in hook_targets.uninstall_all():
        state_text = "removed" if result["removed"] else "not present"
        print(f"{result['shell']}: {state_text} ({result['path']})")
    return 0


def _cmd_hook_status(args) -> int:
    results = hook_targets.status()
    if getattr(args, "json", False):
        payload = {
            "installed": any(r["hook_present"] for r in results),
            "installed_at": state.get_hook_installed_at(),
            "shells": [
                {"shell": r["shell"], "path": str(r["path"]), "hook_present": r["hook_present"]}
                for r in results
            ],
            "active_sessions": [
                {
                    "pid": s["pid"],
                    "project_path": s["project_path"],
                    "log_path": s["log_path"],
                    "started_at": s["started_at"],
                    "last_activity_at": s.get("last_activity_at"),
                }
                for s in state.list_active_sessions()
            ],
            "limitations": HOOK_STATUS_LIMITATIONS,
        }
        print(json.dumps(payload, indent=2))
        return 0

    for result in results:
        state_text = "installed" if result["hook_present"] else "not installed"
        print(f"{result['shell']}: {state_text} ({result['path']})")
    return 0


def _cmd_service_start(args) -> int:
    if args.all:
        services = config.load_config()["services"]
        exit_code = 0
        for service in services:
            service_name = service["name"]
            try:
                pid = service_manager.start(service_name, os.getcwd())
            except ValueError as exc:
                print(str(exc), file=sys.stderr)
                exit_code = 1
                continue
            print(f"started {service_name} (pid {pid})")
        return exit_code

    try:
        pid = service_manager.start(args.name, os.getcwd())
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(f"started {args.name} (pid {pid})")
    return 0


def _cmd_service_stop(args) -> int:
    stopped = service_manager.stop(args.name, os.getcwd())
    print(f"stopped {args.name}" if stopped else f"{args.name} was not running")
    return 0


def _cmd_service_status(args) -> int:
    for entry in service_manager.status(os.getcwd()):
        state = f"running (pid {entry['pid']})" if entry["running"] else "stopped"
        print(f"{entry['name']}: {state}")
        if entry["log_path"]:
            print(f"  log: {entry['log_path']}")
    return 0


def _cmd_service_logs(args) -> int:
    entry = None
    for candidate in service_manager.status(os.getcwd()):
        if candidate["name"] == args.name:
            entry = candidate
            break
    if entry is None or not entry["log_path"]:
        print(f"no active log for {args.name}", file=sys.stderr)
        return 1

    with open(entry["log_path"], "r", encoding="utf-8", errors="replace") as f:
        print(f.read(), end="")
        if not args.follow:
            return 0

        while True:
            line = f.readline()
            if line:
                print(line, end="")
            else:
                time.sleep(0.5)


def _cmd_log_view(args) -> int:
    try:
        f = open(args.path, "r", encoding="utf-8", errors="replace")
    except OSError as exc:
        print(f"could not read {args.path}: {exc}", file=sys.stderr)
        return 1

    with f:
        if args.tail:
            lines = f.readlines()[-args.tail:]
            cleaned = ansi.strip_ansi("".join(lines))
            if args.out:
                with open(args.out, "w", encoding="utf-8") as out:
                    out.write(cleaned)
                print(f"wrote plain-text log to {args.out}")
            else:
                print(cleaned, end="")
            return 0

        if args.follow:
            out = open(args.out, "w", encoding="utf-8") if args.out else None
            try:
                while True:
                    line = f.readline()
                    if line:
                        cleaned = ansi.strip_ansi(line)
                        if out:
                            out.write(cleaned)
                            out.flush()
                        else:
                            print(cleaned, end="", flush=True)
                    else:
                        time.sleep(0.5)
            finally:
                if out:
                    out.close()

        raw = f.read()
        cleaned = ansi.strip_ansi(raw)

        if args.out:
            with open(args.out, "w", encoding="utf-8") as out:
                out.write(cleaned)
            print(f"wrote plain-text log to {args.out}")
        else:
            print(cleaned, end="")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="termlog",
        description="Record local dev terminal sessions and managed service logs.",
    )
    subparsers = parser.add_subparsers(dest="topic", required=True)

    hook_parser = subparsers.add_parser(
        "hook", help="control automatic recording of future interactive terminals"
    )
    hook_sub = hook_parser.add_subparsers(dest="action", required=True)
    hook_sub.add_parser(
        "install",
        help="install the shell hook; every new interactive terminal opened after this "
        "will be recorded until 'hook uninstall' is run",
    ).set_defaults(func=_cmd_hook_install)
    hook_sub.add_parser(
        "uninstall",
        help="remove the shell hook (new terminals stop being recorded) and export "
        "plain-text copies of logs captured since install",
    ).set_defaults(func=_cmd_hook_uninstall)
    status_parser = hook_sub.add_parser(
        "status", help="show whether the hook is installed and which sessions are recording now"
    )
    status_parser.add_argument(
        "--json",
        action="store_true",
        help="machine-readable output: install state, active recording sessions "
        "(pid/project/log path), and known limitations",
    )
    status_parser.set_defaults(func=_cmd_hook_status)

    service_parser = subparsers.add_parser(
        "service", help="start/stop/monitor a long-running dev service and capture its output"
    )
    service_sub = service_parser.add_subparsers(dest="action", required=True)

    start_parser = service_sub.add_parser(
        "start", help="launch a service defined in ~/.termlog/termlog.yaml and start logging it"
    )
    start_group = start_parser.add_mutually_exclusive_group(required=True)
    start_group.add_argument("name", nargs="?", help="service name from termlog.yaml")
    start_group.add_argument("--all", action="store_true", help="start every configured service")
    start_parser.set_defaults(func=_cmd_service_start)

    stop_parser = service_sub.add_parser("stop", help="stop a running service")
    stop_parser.add_argument("name", help="service name from termlog.yaml")
    stop_parser.set_defaults(func=_cmd_service_stop)

    service_sub.add_parser(
        "status", help="list configured services and whether each is currently running"
    ).set_defaults(func=_cmd_service_status)

    logs_parser = service_sub.add_parser("logs", help="print a running service's captured output")
    logs_parser.add_argument("name", help="service name from termlog.yaml")
    logs_parser.add_argument(
        "-f", "--follow", action="store_true", help="keep printing new output as it's written"
    )
    logs_parser.set_defaults(func=_cmd_service_logs)

    log_parser = subparsers.add_parser("log", help="read raw captured log files as plain text")
    log_sub = log_parser.add_subparsers(dest="action", required=True)

    view_parser = log_sub.add_parser(
        "view",
        help="strip ANSI/control escape sequences from a captured log so it reads as "
        "clean text; does not modify the original log file",
    )
    view_parser.add_argument("path", help="path to a .log file under ~/.termlog/logs/...")
    view_parser.add_argument("--out", help="write the cleaned text to this file instead of stdout")
    view_parser.add_argument(
        "-f",
        "--follow",
        action="store_true",
        help="keep streaming cleaned text as the log grows (for a session still recording)",
    )
    view_parser.add_argument(
        "--tail",
        type=int,
        metavar="N",
        help="only show the last N lines (use this instead of a full read when "
        "looking for a recent error, to avoid pulling an entire large log into context)",
    )
    view_parser.set_defaults(func=_cmd_log_view)

    return parser


def main(argv=None) -> int:
    cleanup.run_cleanup()
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
