import argparse
import os
import sys

from termlog import cleanup, config, hook_targets, service_manager


def _cmd_hook_install(args) -> int:
    for result in hook_targets.install_all():
        state = "installed" if result["installed"] else "already up to date"
        print(f"{result['shell']}: {state} ({result['path']})")
    return 0


def _cmd_hook_uninstall(args) -> int:
    for result in hook_targets.uninstall_all():
        state = "removed" if result["removed"] else "not present"
        print(f"{result['shell']}: {state} ({result['path']})")
    return 0


def _cmd_hook_status(args) -> int:
    for result in hook_targets.status():
        state = "installed" if result["hook_present"] else "not installed"
        print(f"{result['shell']}: {state} ({result['path']})")
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
        import time

        while True:
            line = f.readline()
            if line:
                print(line, end="")
            else:
                time.sleep(0.5)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="termlog")
    subparsers = parser.add_subparsers(dest="topic", required=True)

    hook_parser = subparsers.add_parser("hook")
    hook_sub = hook_parser.add_subparsers(dest="action", required=True)
    hook_sub.add_parser("install").set_defaults(func=_cmd_hook_install)
    hook_sub.add_parser("uninstall").set_defaults(func=_cmd_hook_uninstall)
    hook_sub.add_parser("status").set_defaults(func=_cmd_hook_status)

    service_parser = subparsers.add_parser("service")
    service_sub = service_parser.add_subparsers(dest="action", required=True)

    start_parser = service_sub.add_parser("start")
    start_group = start_parser.add_mutually_exclusive_group(required=True)
    start_group.add_argument("name", nargs="?")
    start_group.add_argument("--all", action="store_true")
    start_parser.set_defaults(func=_cmd_service_start)

    stop_parser = service_sub.add_parser("stop")
    stop_parser.add_argument("name")
    stop_parser.set_defaults(func=_cmd_service_stop)

    service_sub.add_parser("status").set_defaults(func=_cmd_service_status)

    logs_parser = service_sub.add_parser("logs")
    logs_parser.add_argument("name")
    logs_parser.add_argument("-f", "--follow", action="store_true")
    logs_parser.set_defaults(func=_cmd_service_logs)

    return parser


def main(argv=None) -> int:
    cleanup.run_cleanup()
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
