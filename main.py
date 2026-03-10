#!/usr/bin/env python3
"""Thin entrypoint for xyz."""

from __future__ import annotations

import os
import shlex
import subprocess
import sys
from typing import Sequence
from urllib.error import URLError
from urllib.request import Request, urlopen

from models import ValidationError
from orchestrator import Orchestrator
from config import config_file_path

try:
    from _version import __version__
except Exception:  # pragma: no cover - fallback for source runs
    __version__ = "0.0.0"

INSTALL_URL = "https://raw.githubusercontent.com/ryangerardwilson/xyz/main/install.sh"
LATEST_RELEASE_API = "https://api.github.com/repos/ryangerardwilson/xyz/releases/latest"


def _version_tuple(value: str) -> tuple[int, ...]:
    sanitized = value.strip().lower().lstrip("v")
    parts = []
    for chunk in sanitized.split("."):
        try:
            parts.append(int(chunk))
        except ValueError:
            break
    return tuple(parts)


def _fetch_latest_version() -> str | None:
    try:
        req = Request(
            LATEST_RELEASE_API,
            headers={"Accept": "application/vnd.github+json"},
        )
        with urlopen(req, timeout=10) as resp:  # nosec B310
            payload = resp.read()
    except (URLError, TimeoutError):
        return None
    try:
        import json

        data = json.loads(payload)
    except Exception:
        return None
    tag = data.get("tag_name")
    if isinstance(tag, str) and tag.strip():
        return tag.strip().lstrip("v")
    return None


def _run_upgrade() -> int:
    latest_version = _fetch_latest_version()
    if latest_version:
        current_tuple = _version_tuple(__version__)
        latest_tuple = _version_tuple(latest_version)
        if current_tuple and latest_tuple and current_tuple >= latest_tuple:
            print(f"xyz is already up to date (version {__version__}).")
            return 0
    try:
        curl = subprocess.Popen(
            ["curl", "-fsSL", INSTALL_URL],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except FileNotFoundError:
        print("Upgrade requires curl", file=sys.stderr)
        return 1

    try:
        bash = subprocess.Popen(["bash", "-s", "--", "--upgrade"], stdin=curl.stdout)
        if curl.stdout is not None:
            curl.stdout.close()
    except FileNotFoundError:
        print("Upgrade requires bash", file=sys.stderr)
        curl.terminate()
        curl.wait()
        return 1

    bash_rc = bash.wait()
    curl_rc = curl.wait()

    if curl_rc != 0:
        stderr = (
            curl.stderr.read().decode("utf-8", errors="replace") if curl.stderr else ""
        )
        if stderr:
            sys.stderr.write(stderr)
        return curl_rc

    return bash_rc


def _open_config_in_editor() -> int:
    cfg_path = config_file_path()
    if not cfg_path.exists():
        cfg_path.write_text("{}\n", encoding="utf-8")
    editor = (os.environ.get("VISUAL") or os.environ.get("EDITOR") or "vim").strip()
    editor_cmd = shlex.split(editor) if editor else ["vim"]
    if not editor_cmd:
        editor_cmd = ["vim"]
    return subprocess.run([*editor_cmd, str(cfg_path)], check=False).returncode


def _print_help() -> None:
    print(
        "xyz - terminal-native keyboard-first task tracker\n\n"
        "Usage:\n"
        "  xyz tui          Launch curses UI\n"
        "  xyz -h           Show this help\n"
        "  xyz ?            Show x/y/z/p/q/r meanings\n"
        "  xyz conf         Open config in $VISUAL/$EDITOR\n"
        "  xyz -v           Show installed version\n"
        "  xyz -u           Reinstall latest release if newer exists\n"
        "  xyz ls -all|-per|-eco|-tng [count]   List upcoming items\n"
        "  xyz a                                 Add item in $EDITOR\n"
        '  xyz a -x "" -y "" -z "" -p "" -q "" -r "" [-bkt per|tng|eco]\n'
        "  xyz e -id <csv_id>                    Edit by stable CSV id in $EDITOR\n"
        '  xyz e -id <csv_id> -x "" -y "" -p "" [-bkt per|tng|eco]\n'
        "  xyz d -id <csv_id>                    Delete by stable CSV id\n"
    )


def _print_field_meanings() -> None:
    use_color = sys.stdout.isatty() and "NO_COLOR" not in os.environ

    def muted(text: str) -> str:
        if not use_color:
            return text
        return f"\033[90m{text}\033[0m"

    print(
        "Idea:\n"
        "  \"When X happens, I want Y outcome, so that I can drive Z impact\"\n\n"
        "XYZ Fields:\n"
        "  x: target trigger datetime (when outcome should be checked)\n"
        "  y: desired progress/outcome\n"
        "  z: why it matters / impact\n\n"
        "PQR Scores (0-10):\n"
        "  p: Jesus' will alignment\n"
        f"     {muted('How aligned was this with Jesus-like values: love, truth, humility, stewardship?')}\n"
        "  q: outward impact\n"
        f"     {muted('What good did it create in the world around you: work, family, service, finances?')}\n"
        "  r: embodied practice\n"
        f"     {muted('Did I honour my body and nervous system while doing it, or did I sacrifice them?')}\n"
    )


def _parse_positive_int(raw: str, label: str) -> int:
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValidationError(f"{label} must be an integer") from exc
    if value <= 0:
        raise ValidationError(f"{label} must be >= 1")
    return value


def _parse_command_flags(
    args: Sequence[str], *, allowed: set[str]
) -> dict[str, str]:
    parsed: dict[str, str] = {}
    idx = 0
    while idx < len(args):
        key = args[idx]
        if not key.startswith("-"):
            raise ValidationError(f"Unexpected argument '{key}'")
        if key not in allowed:
            raise ValidationError(f"Unknown flag '{key}'")
        idx += 1
        if idx >= len(args):
            raise ValidationError(f"{key} requires a value")
        parsed[key] = args[idx]
        idx += 1
    return parsed


def parse_args(
    argv: Sequence[str],
) -> tuple[bool, bool, bool, str | None, list[str]]:
    show_version = False
    show_help = False
    do_upgrade = False
    command: str | None = None
    command_args: list[str] = []

    if argv and argv[0] in {"?", "tui", "ls", "a", "e", "d", "conf"}:
        command = argv[0]
        command_args = list(argv[1:])
        return show_version, show_help, do_upgrade, command, command_args

    idx = 0
    while idx < len(argv):
        arg = argv[idx]
        if arg == "-h":
            show_help = True
            idx += 1
            continue
        if arg == "-v":
            show_version = True
            idx += 1
            continue
        if arg == "-u":
            do_upgrade = True
            idx += 1
            continue
        raise ValidationError(f"Unknown flag '{arg}'")
    return show_version, show_help, do_upgrade, command, command_args


def main(argv: list[str] | None = None) -> int:
    # Make ESC detection snappy inside curses.
    os.environ.setdefault("ESCDELAY", "25")

    if argv is None:
        argv = sys.argv[1:]

    try:
        (
            show_version,
            show_help,
            do_upgrade,
            command,
            command_args,
        ) = parse_args(argv)
    except ValidationError as exc:
        print(str(exc))
        return 1

    if show_version:
        print(__version__)
        return 0

    if show_help:
        _print_help()
        return 0

    if do_upgrade:
        return _run_upgrade()

    orchestrator = Orchestrator()
    try:
        if command == "?":
            if command_args:
                print("Usage: xyz ?")
                return 1
            _print_field_meanings()
            return 0
        if command == "conf":
            if command_args:
                print("Usage: xyz conf")
                return 1
            return _open_config_in_editor()
        if command == "tui":
            if command_args:
                print("Usage: xyz tui")
                return 1
            return orchestrator.run()
        if command == "ls":
            bucket = "-all"
            count: int | None = None
            if command_args:
                first = command_args[0]
                if first in {"-all", "-per", "-eco", "-tng"}:
                    bucket = first
                    if len(command_args) > 1:
                        count = _parse_positive_int(command_args[1], "List count")
                    if len(command_args) > 2:
                        print("Usage: xyz ls -all|-per|-eco|-tng [count]")
                        return 1
                else:
                    count = _parse_positive_int(first, "List count")
                    if len(command_args) > 1:
                        print("Usage: xyz ls -all|-per|-eco|-tng [count]")
                        return 1
            return orchestrator.list_upcoming_cli(bucket, count)
        if command == "a":
            if not command_args:
                return orchestrator.add_via_editor_cli()
            flags = _parse_command_flags(
                command_args, allowed={"-x", "-y", "-z", "-p", "-q", "-r", "-bkt"}
            )
            required = {"-x", "-y", "-z", "-p", "-q", "-r"}
            missing = [flag for flag in required if flag not in flags]
            if missing:
                missing.sort()
                print(
                    "Missing required flag(s): "
                    + ", ".join(missing)
                    + " for direct add"
                )
                return 1
            return orchestrator.add_direct_cli(
                {
                    "x": flags["-x"],
                    "y": flags["-y"],
                    "z": flags["-z"],
                    "p": flags["-p"],
                    "q": flags["-q"],
                    "r": flags["-r"],
                    "bkt": flags.get("-bkt", ""),
                }
            )
        if command == "e":
            if not command_args:
                print("Usage: xyz e -id <csv_id> | xyz e -id <csv_id> -x ...")
                return 1
            flags = _parse_command_flags(
                command_args,
                allowed={"-id", "-x", "-y", "-z", "-p", "-q", "-r", "-bkt"},
            )
            updates: dict[str, str] = {}
            for key, value in flags.items():
                clean_key = key.lstrip("-")
                updates[clean_key] = value

            if "id" not in updates:
                print("Missing required flag: -id")
                return 1
            item_id = _parse_positive_int(updates["id"], "ID")
            del updates["id"]

            if not updates:
                return orchestrator.edit_by_id_cli(item_id)
            return orchestrator.edit_by_id_direct_cli(item_id, updates)
        if command == "d":
            flags = _parse_command_flags(command_args, allowed={"-id"})
            if "-id" not in flags:
                print("Usage: xyz d -id <csv_id>")
                return 1
            item_id = _parse_positive_int(flags["-id"], "ID")
            return orchestrator.delete_by_id_cli(item_id)
    except ValidationError as exc:
        print(str(exc))
        return 1

    _print_help()
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
