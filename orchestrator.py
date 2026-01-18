#!/usr/bin/env python3
"""Placeholder orchestrator for tcal."""
from __future__ import annotations

import argparse
import curses
from typing import List, Sequence


class Orchestrator:
    """Owns CLI parsing and the curses lifecycle."""

    def __init__(self, version: str = "0.0.0") -> None:
        self.version = version

    def run(self, *, argv: Sequence[str]) -> int:
        parser = argparse.ArgumentParser(prog="tcal")
        parser.add_argument("--version", action="store_true", help="Show version and exit")
        parser.add_argument("--help-only", action="store_true", help=argparse.SUPPRESS)

        args = parser.parse_args(list(argv))

        if args.version:
            print(self.version)
            return 0

        if args.help_only:
            parser.print_help()
            return 0

        return self._run_curses()

    def _run_curses(self) -> int:
        try:
            curses.wrapper(self._curses_main)
        except curses.error:
            return 1
        return 0

    def _curses_main(self, stdscr: "curses._CursesWindow") -> None:  # type: ignore[name-defined]
        curses.curs_set(0)
        stdscr.nodelay(False)
        stdscr.timeout(100)

        self._draw_static_ui(stdscr)

        while True:
            ch = stdscr.getch()
            if ch in (-1, curses.ERR):
                continue
            if ch in (ord("q"), ord("Q")):
                break
            if ch == ord("?"):
                self._draw_help_overlay(stdscr)
            else:
                self._draw_static_ui(stdscr)

    def _draw_static_ui(self, stdscr: "curses._CursesWindow") -> None:  # type: ignore[name-defined]
        stdscr.erase()
        h, w = stdscr.getmaxyx()

        title = "tcal — Vim-first terminal calendar"
        hint = "q: quit    ?: help"

        stdscr.addnstr(0, 0, title.ljust(w), w)
        stdscr.addnstr(2, 0, "Skeleton build: navigation/event flows coming soon."[: w], w)
        stdscr.addnstr(h - 1, 0, hint.ljust(w), w)
        stdscr.refresh()

    def _draw_help_overlay(self, stdscr: "curses._CursesWindow") -> None:  # type: ignore[name-defined]
        h, w = stdscr.getmaxyx()
        lines: List[str] = [
            "tcal help",
            "",
            "q        quit",
            "?        toggle this help",
            "",
            "Roadmap: month view, day pane, event CRUD",
            "Press any key to return",
        ]
        win_h = min(len(lines) + 2, h - 2)
        win_w = min(max(len(line) for line in lines) + 4, w - 2)
        win_y = (h - win_h) // 2
        win_x = (w - win_w) // 2

        win = stdscr.derwin(win_h, win_w, win_y, win_x)
        win.border()
        for idx, line in enumerate(lines, start=1):
            win.addnstr(idx, 2, line[: win_w - 4], win_w - 4)
        win.refresh()

        while True:
            if stdscr.getch() != -1:
                break

        self._draw_static_ui(stdscr)


__all__ = ["Orchestrator"]
