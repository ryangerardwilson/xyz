#!/usr/bin/env python3
"""Thin entrypoint for xyz."""

from __future__ import annotations

import os
import subprocess
import sys
from typing import Sequence
from urllib.error import URLError
from urllib.request import Request, urlopen

from models import ValidationError
from orchestrator import Orchestrator

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


def _print_help() -> None:
    print(
        "xyz - terminal-native keyboard-first task tracker\n\n"
        "Usage:\n"
        "  xyz              Launch curses UI\n"
        "  xyz -h           Show this help\n"
        "  xyz -v           Show installed version\n"
        "  xyz -u           Reinstall latest release if newer exists\n"
        '  xyz -b "<bucket>" -x "<YYYY-MM-DD HH:MM[:SS]>" -y "<outcome>" -z "<impact>"\n'
    )


def parse_args(argv: Sequence[str]) -> tuple[dict[str, str | None], bool, bool, bool]:
    flags: dict[str, str | None] = {}
    show_version = False
    show_help = False
    do_upgrade = False

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
        if arg == "-x":
            idx += 1
            if idx >= len(argv):
                raise ValidationError("-x requires a datetime argument")
            flags["x"] = argv[idx]
            idx += 1
            continue
        if arg == "-y":
            idx += 1
            if idx >= len(argv):
                raise ValidationError("-y requires an outcome argument")
            flags["y"] = argv[idx]
            idx += 1
            continue
        if arg == "-z":
            idx += 1
            if idx >= len(argv):
                raise ValidationError("-z requires an impact argument")
            flags["z"] = argv[idx]
            idx += 1
            continue
        if arg == "-b":
            idx += 1
            if idx >= len(argv):
                raise ValidationError("-b requires a bucket argument")
            flags["b"] = argv[idx]
            idx += 1
            continue
        raise ValidationError(f"Unknown flag '{arg}'")
    return flags, show_version, show_help, do_upgrade


def main(argv: list[str] | None = None) -> int:
    # Make ESC detection snappy inside curses.
    os.environ.setdefault("ESCDELAY", "25")

    if argv is None:
        argv = sys.argv[1:]

    try:
        flag_values, show_version, show_help, do_upgrade = parse_args(argv)
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

    cli_flags = {"b", "x", "y", "z"}
    if any(flag in flag_values for flag in cli_flags):
        missing = [flag for flag in ("b", "x", "y", "z") if flag_values.get(flag) is None]
        if missing:
            print(
                f"Missing required flag(s): {', '.join(f'-{flag}' for flag in missing)}"
            )
            return 1
        x_val = flag_values.get("x") or ""
        y_val = flag_values.get("y") or ""
        z_val = flag_values.get("z") or ""
        bucket_val = flag_values.get("b") or ""
        return orchestrator.handle_structured_cli(bucket_val, x_val, y_val, z_val)

    return orchestrator.run()


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
