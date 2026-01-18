#!/usr/bin/env python3
"""Thin entrypoint for tcal."""

from __future__ import annotations

import os
import subprocess
import sys
from typing import Sequence

from orchestrator import Orchestrator

try:
    from _version import __version__
except Exception:  # pragma: no cover - fallback for source runs
    __version__ = "0.0.0"

INSTALL_URL = "https://raw.githubusercontent.com/ryangerardwilson/tcal/main/install.sh"


def _run_upgrade() -> int:
    try:
        curl = subprocess.Popen(
            ["curl", "-fsSL", INSTALL_URL], stdout=subprocess.PIPE, stderr=subprocess.PIPE
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
        stderr = curl.stderr.read().decode("utf-8", errors="replace") if curl.stderr else ""
        if stderr:
            sys.stderr.write(stderr)
        return curl_rc

    return bash_rc


def _print_help() -> None:
    print(
        "tcal - terminal-native keyboard-first calendar\n\n"
        "Usage:\n"
        "  tcal                 Launch curses UI\n"
        "  tcal --version       Show installed version\n"
        "  tcal --upgrade       Reinstall latest release if newer exists\n"
        "  tcal <natural text>  Run natural-language CLI query\n"
    )


def parse_args(argv: Sequence[str]) -> tuple[list[str], bool, bool, bool]:
    remaining: list[str] = []
    show_version = False
    show_help = False
    do_upgrade = False

    skip_next = False
    for idx, arg in enumerate(argv):
        if skip_next:
            skip_next = False
            continue
        if arg in {"-h", "--help"}:
            show_help = True
        elif arg in {"-V", "--version"}:
            show_version = True
        elif arg == "--upgrade":
            do_upgrade = True
        else:
            remaining.append(arg)
    return remaining, show_version, show_help, do_upgrade


def main(argv: list[str] | None = None) -> int:
    # Make ESC detection snappy inside curses.
    os.environ.setdefault("ESCDELAY", "25")

    if argv is None:
        argv = sys.argv[1:]

    remaining, show_version, show_help, do_upgrade = parse_args(argv)

    if show_version:
        print(__version__)
        return 0

    if show_help:
        _print_help()
        return 0

    if do_upgrade:
        return _run_upgrade()

    orchestrator = Orchestrator()
    if remaining:
        # Natural-language CLI flow: treat all remaining args as a single description.
        nl_input = " ".join(remaining)
        return orchestrator.handle_nl_cli(nl_input)

    return orchestrator.run()


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
