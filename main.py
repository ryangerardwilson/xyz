#!/usr/bin/env python3
"""Thin entrypoint for tcal."""
from __future__ import annotations

import os
import sys

from orchestrator import Orchestrator


def main() -> int:
    # Make ESC detection snappy inside curses.
    os.environ.setdefault("ESCDELAY", "25")

    orchestrator = Orchestrator()
    return orchestrator.run(argv=sys.argv[1:])


if __name__ == "__main__":
    sys.exit(main())
