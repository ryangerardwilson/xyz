#!/usr/bin/env python3
"""Thin entrypoint for tcal."""

from __future__ import annotations

import os
import sys

from orchestrator import Orchestrator


def main(argv: list[str] | None = None) -> int:
    # Make ESC detection snappy inside curses.
    os.environ.setdefault("ESCDELAY", "25")

    if argv is None:
        argv = sys.argv[1:]

    orchestrator = Orchestrator()
    if argv:
        # Natural-language CLI flow: treat all args as a single description.
        nl_input = " ".join(argv)
        return orchestrator.handle_nl_cli(nl_input)

    return orchestrator.run()


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
