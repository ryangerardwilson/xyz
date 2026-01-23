#!/usr/bin/env python3
"""Agenda view rendering and interactions."""

from __future__ import annotations

import curses
import textwrap
from datetime import datetime
from typing import List

from models import Event
from ui_base import clamp

_TIMESTAMP_FMT = "%Y-%m-%d %H:%M"
_MIN_X_WIDTH = 6
_MAX_X_WIDTH = 19
_MIN_Y_WIDTH = 6
_MAX_Y_WIDTH = 60
_MIN_Z_WIDTH = 6
_MAX_Z_WIDTH = 40
_GAP_WIDTH = 1
_NO_TASKS_MESSAGE = "No tasks yet. Press i to create."


def _max_line_length(text: str) -> int:
    if not text:
        return 0
    lines = text.splitlines()
    if not lines:
        return len(text)
    return max(len(line) for line in lines)


def _wrap_text(value: str, width: int) -> List[str]:
    if width <= 0:
        return [""]
    text = "" if value is None else str(value)
    parts = text.splitlines()
    if not parts:
        parts = [text]
    lines: List[str] = []
    for part in parts:
        if part == "":
            lines.append("")
            continue
        wrapped = textwrap.wrap(
            part,
            width=width,
            break_long_words=True,
            drop_whitespace=False,
            replace_whitespace=False,
        )
        if not wrapped:
            lines.append("")
        else:
            lines.extend(wrapped)
    return lines or [""]


class AgendaView:
    def __init__(self, events: List[Event]):
        self.events = events

    COLUMN_COUNT = 3

    def render(
        self,
        stdscr: "curses.window",
        selected_idx: int,
        scroll: int,
        *,
        expand_all: bool = True,
        selected_col: int = 0,
    ) -> int:  # type: ignore[name-defined]
        h, w = stdscr.getmaxyx()
        usable_h = h - 1
        usable_w = max(0, w - 1)

        if usable_h <= 0 or usable_w <= 0:
            return 0 if not self.events else clamp(scroll, 0, max(0, len(self.events) - 1))

        selected_col = clamp(selected_col, 0, self.COLUMN_COUNT - 1)

        timestamps = [ev.x.strftime(_TIMESTAMP_FMT) for ev in self.events]
        y_values = ["" if ev.y is None else str(ev.y) for ev in self.events]
        z_values = ["" if ev.z is None else str(ev.z) for ev in self.events]

        max_x_len = max((len(val) for val in timestamps), default=len("x"))
        max_y_len = max((_max_line_length(val) for val in y_values), default=len("y"))
        max_z_len = max((_max_line_length(val) for val in z_values), default=len("z"))

        x_width = max(_MIN_X_WIDTH, min(_MAX_X_WIDTH, max(len("x"), max_x_len)))
        y_width = max(_MIN_Y_WIDTH, min(_MAX_Y_WIDTH, max(len("y"), max_y_len)))
        z_width = max(_MIN_Z_WIDTH, min(_MAX_Z_WIDTH, max(len("z"), max_z_len)))

        widths = [x_width, y_width, z_width]
        minimums = [_MIN_X_WIDTH, _MIN_Y_WIDTH, _MIN_Z_WIDTH]
        total_width = sum(widths) + 2 * _GAP_WIDTH

        if total_width > usable_w:
            while total_width > usable_w and any(cur > minimum for cur, minimum in zip(widths, minimums)):
                largest_idx = max(range(3), key=lambda idx: widths[idx])
                if widths[largest_idx] <= minimums[largest_idx]:
                    break
                widths[largest_idx] -= 1
                total_width -= 1

        if total_width > usable_w:
            idx_iter = 0
            while total_width > usable_w and any(value > 1 for value in widths):
                if widths[idx_iter] > 1:
                    widths[idx_iter] -= 1
                    total_width -= 1
                idx_iter = (idx_iter + 1) % 3

        if total_width > usable_w and usable_w > 0:
            overflow = total_width - usable_w
            for idx in range(3):
                if overflow <= 0:
                    break
                reducible = widths[idx] - 1
                if reducible <= 0:
                    continue
                delta = min(reducible, overflow)
                widths[idx] -= delta
                overflow -= delta
                total_width -= delta

        x_width, y_width, z_width = [max(1, width) for width in widths]
        total_width = x_width + y_width + z_width + 2 * _GAP_WIDTH

        if total_width > usable_w and usable_w > 0:
            return clamp(scroll, 0, max(0, len(self.events) - 1))

        x_start = 0
        y_start = x_start + x_width + _GAP_WIDTH
        z_start = y_start + y_width + _GAP_WIDTH
        tail_width = max(0, usable_w - (z_start + z_width))

        def write(y: int, x: int, width: int, text: str, attr: int = 0) -> None:
            if width <= 0 or y < 0 or y >= usable_h:
                return
            if x >= usable_w:
                return
            span = min(width, max(0, usable_w - x))
            if span <= 0:
                return
            try:
                stdscr.addnstr(y, x, text[:span].ljust(span), span, attr)
            except curses.error:
                pass

        header_y = 0
        write(header_y, x_start, x_width, "x", curses.A_BOLD)
        write(header_y, x_start + x_width, _GAP_WIDTH, " " * _GAP_WIDTH, curses.A_BOLD)
        write(header_y, y_start, y_width, "y", curses.A_BOLD)
        write(header_y, y_start + y_width, _GAP_WIDTH, " " * _GAP_WIDTH, curses.A_BOLD)
        write(header_y, z_start, z_width, "z", curses.A_BOLD)
        if tail_width > 0:
            write(header_y, z_start + z_width, tail_width, "", curses.A_BOLD)

        data_top = 1
        data_height = usable_h - 1
        if data_height <= 0:
            return 0 if not self.events else clamp(scroll, 0, max(0, len(self.events) - 1))

        if not self.events:
            write(data_top, 0, usable_w, _NO_TASKS_MESSAGE[:usable_w])
            return 0

        rows = []
        for idx, timestamp in enumerate(timestamps):
            y_lines_full = _wrap_text(y_values[idx], y_width)
            z_lines_full = _wrap_text(z_values[idx], z_width)
            y_lines = y_lines_full if expand_all else y_lines_full[:1]
            z_lines = z_lines_full if expand_all else z_lines_full[:1]
            y_lines = y_lines or [""]
            z_lines = z_lines or [""]
            height = max(len(y_lines), len(z_lines))
            rows.append(
                {
                    "x": timestamp,
                    "y_lines": y_lines,
                    "z_lines": z_lines,
                    "height": max(1, height),
                }
            )

        total_rows = len(rows)
        selected_idx = clamp(selected_idx, 0, total_rows - 1)
        scroll = clamp(scroll, 0, total_rows - 1)

        row_heights = [row["height"] for row in rows]

        def compute_visible(start_idx: int) -> List[int]:
            if start_idx < 0:
                start_idx = 0
            visible: List[int] = []
            used = 0
            idx = start_idx
            while idx < total_rows:
                height = max(1, row_heights[idx])
                if used + height > data_height:
                    if not visible:
                        visible.append(idx)
                    break
                visible.append(idx)
                used += height
                if used >= data_height:
                    break
                idx += 1
            return visible

        if scroll > selected_idx:
            scroll = selected_idx

        visible = compute_visible(scroll)
        while selected_idx not in visible and scroll < total_rows - 1:
            scroll += 1
            visible = compute_visible(scroll)

        if selected_idx not in visible:
            scroll = selected_idx
            visible = compute_visible(scroll)

        def _height_sum(indices: List[int]) -> int:
            return sum(row_heights[i] for i in indices)

        while scroll > 0:
            prev_visible = compute_visible(scroll - 1)
            if selected_idx not in prev_visible:
                break
            if _height_sum(prev_visible) > data_height:
                break
            scroll -= 1
            visible = prev_visible

        if not visible:
            visible = [selected_idx]
            scroll = selected_idx

        y_cursor = data_top
        data_bottom = data_top + data_height

        for idx in visible:
            row = rows[idx]
            row_lines = max(1, row["height"])
            y_lines = row["y_lines"]
            z_lines = row["z_lines"]
            attr_x_base = curses.A_REVERSE if (idx == selected_idx and selected_col == 0) else 0
            attr_y_base = curses.A_REVERSE if (idx == selected_idx and selected_col == 1) else 0
            attr_z_base = curses.A_REVERSE if (idx == selected_idx and selected_col == 2) else 0
            for line_offset in range(row_lines):
                if y_cursor >= data_bottom:
                    break
                x_text = row["x"] if line_offset == 0 else ""
                write(y_cursor, x_start, x_width, x_text, attr_x_base)
                write(y_cursor, x_start + x_width, _GAP_WIDTH, " " * _GAP_WIDTH, attr_x_base)
                y_text = y_lines[line_offset] if line_offset < len(y_lines) else ""
                write(y_cursor, y_start, y_width, y_text, attr_y_base)
                write(y_cursor, y_start + y_width, _GAP_WIDTH, " " * _GAP_WIDTH, attr_y_base)
                z_text = z_lines[line_offset] if line_offset < len(z_lines) else ""
                write(y_cursor, z_start, z_width, z_text, attr_z_base)
                if tail_width > 0:
                    write(y_cursor, z_start + z_width, tail_width, "", 0)
                y_cursor += 1
            if y_cursor >= data_bottom:
                break

        return scroll

    def clamp_column(self, col: int) -> int:
        return clamp(col, 0, self.COLUMN_COUNT - 1)

    def move_selection(self, selected_idx: int, delta: int) -> int:
        if not self.events:
            return 0
        return clamp(selected_idx + delta, 0, len(self.events) - 1)

    def jump_to_today(self) -> int:
        if not self.events:
            return 0
        today = datetime.today()
        for idx, ev in enumerate(self.events):
            if ev.x >= today:
                return idx
        return len(self.events) - 1


__all__ = ["AgendaView"]
