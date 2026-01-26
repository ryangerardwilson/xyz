#!/usr/bin/env python3
"""Basic UI helpers for curses rendering."""

from __future__ import annotations

import curses
from typing import Iterable


_BOX_COLOR_PAIR: int | None = None


def _box_color_attr() -> int:
    global _BOX_COLOR_PAIR
    if _BOX_COLOR_PAIR is not None:
        return _BOX_COLOR_PAIR
    if not curses.has_colors():
        _BOX_COLOR_PAIR = 0
        return _BOX_COLOR_PAIR
    try:
        curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLACK)
    except curses.error:
        _BOX_COLOR_PAIR = 0
        return _BOX_COLOR_PAIR
    _BOX_COLOR_PAIR = curses.color_pair(1)
    return _BOX_COLOR_PAIR


def draw_header(stdscr: "curses.window", text: str) -> None:  # type: ignore[name-defined]
    h, w = stdscr.getmaxyx()
    if w <= 0 or h <= 0:
        return
    stdscr.addnstr(0, 0, text.ljust(max(1, w - 1)), max(0, w - 1))


def draw_footer(stdscr: "curses.window", text: str) -> None:  # type: ignore[name-defined]
    h, w = stdscr.getmaxyx()
    if w <= 0 or h <= 0:
        return
    stdscr.addnstr(h - 1, 0, text.ljust(max(1, w - 1)), max(0, w - 1))


def draw_centered_box(stdscr: "curses._CursesWindow", lines: Iterable[str]) -> None:  # type: ignore[name-defined]
    h, w = stdscr.getmaxyx()
    lines_list = list(lines)
    win_h = min(len(lines_list) + 2, h - 2)
    win_w = min(max(len(line) for line in lines_list) + 4, w - 2)
    win_y = (h - win_h) // 2
    win_x = (w - win_w) // 2
    win = stdscr.derwin(win_h, win_w, win_y, win_x)
    attr = _box_color_attr()
    if attr:
        win.bkgd(" ", attr)
        win.attrset(attr)
    win.erase()
    win.border()
    for idx, line in enumerate(lines_list, start=1):
        if attr:
            win.addnstr(idx, 2, line[: win_w - 4], win_w - 4, attr)
        else:
            win.addnstr(idx, 2, line[: win_w - 4], win_w - 4)
    win.refresh()


def clamp(value: int, min_value: int, max_value: int) -> int:
    return max(min_value, min(value, max_value))


__all__ = ["draw_header", "draw_footer", "draw_centered_box", "clamp"]
