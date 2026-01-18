#!/usr/bin/env python3
"""Basic UI helpers for curses rendering."""
from __future__ import annotations

import curses
from typing import Iterable, Tuple


def draw_header(stdscr: "curses._CursesWindow", text: str) -> None:  # type: ignore[name-defined]
    h, w = stdscr.getmaxyx()
    stdscr.addnstr(0, 0, text.ljust(w), w)


def draw_footer(stdscr: "curses._CursesWindow", text: str) -> None:  # type: ignore[name-defined]
    h, w = stdscr.getmaxyx()
    stdscr.addnstr(h - 1, 0, text.ljust(w), w)


def draw_centered_box(stdscr: "curses._CursesWindow", lines: Iterable[str]) -> None:  # type: ignore[name-defined]
    h, w = stdscr.getmaxyx()
    lines_list = list(lines)
    win_h = min(len(lines_list) + 2, h - 2)
    win_w = min(max(len(line) for line in lines_list) + 4, w - 2)
    win_y = (h - win_h) // 2
    win_x = (w - win_w) // 2
    win = stdscr.derwin(win_h, win_w, win_y, win_x)
    win.border()
    for idx, line in enumerate(lines_list, start=1):
        win.addnstr(idx, 2, line[: win_w - 4], win_w - 4)
    win.refresh()


def clamp(value: int, min_value: int, max_value: int) -> int:
    return max(min_value, min(value, max_value))


__all__ = ["draw_header", "draw_footer", "draw_centered_box", "clamp"]
