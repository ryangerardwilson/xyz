#!/usr/bin/env python3
"""Thin entrypoint for xyz."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Sequence

from models import ValidationError
from orchestrator import Orchestrator
from config import config_file_path
from rgw_cli_contract import AppSpec, resolve_install_script_path, run_app

from _version import __version__

INSTALL_SCRIPT = resolve_install_script_path(__file__)
HELP_TEXT = """xyz

flags:
  xyz -h
    show this help
  xyz -v
    print the installed version
  xyz -u
    upgrade to the latest release
  xyz conf
    open config in $VISUAL/$EDITOR

features:
  launch the tui or ask for field meanings
  # xyz tui | xyz ?
  xyz tui
  xyz ?

  list, add, edit, and delete jobs-to-be-done outcomes
  # xyz ls [count] | xyz a | xyz e -id <id> | xyz d -id <id>
  xyz ls 10
  xyz a
  xyz e -id 3
  xyz d -id 3
"""


def _print_help() -> None:
    print(HELP_TEXT)


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
) -> tuple[str | None, list[str]]:
    command: str | None = None
    command_args: list[str] = []

    if argv and argv[0] in {"?", "tui", "ls", "a", "e", "d", "conf"}:
        command = argv[0]
        command_args = list(argv[1:])
        return command, command_args

    idx = 0
    while idx < len(argv):
        arg = argv[idx]
        raise ValidationError(f"Unknown flag '{arg}'")
    return command, command_args


def _dispatch(argv: list[str]) -> int:
    # Make ESC detection snappy inside curses.
    os.environ.setdefault("ESCDELAY", "25")

    try:
        command, command_args = parse_args(argv)
    except ValidationError as exc:
        print(str(exc))
        return 1

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


APP_SPEC = AppSpec(
    app_name="xyz",
    version=__version__,
    help_text=HELP_TEXT,
    install_script_path=INSTALL_SCRIPT,
    no_args_mode="help",
    config_path_factory=config_file_path,
)


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    return run_app(APP_SPEC, args, _dispatch)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
