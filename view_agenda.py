#!/usr/bin/env python3
"""Agenda view rendering and interactions."""

from __future__ import annotations

import curses
import textwrap
from datetime import datetime
from typing import List, Sequence

from models import Event
from ui_base import clamp

_TIMESTAMP_FMT = "%Y-%m-%d %H:%M"
_MIN_X_WIDTH = 6
_MAX_X_WIDTH = 19
_MIN_Y_WIDTH = 6
_MAX_Y_WIDTH = 60
_MIN_Z_WIDTH = 6
_MAX_Z_WIDTH = 40
_MIN_NSM_WIDTH = 6
_MAX_NSM_WIDTH = 12
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
    parts = text.splitlines() or [text]
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


def _event_identity(
    event: Event,
) -> tuple[str, datetime, str, str, float, float, float]:
    return (
        event.bucket,
        event.jtbd.x,
        event.jtbd.y,
        event.jtbd.z,
        event.nsm.p,
        event.nsm.q,
        event.nsm.r,
    )


def _format_nsm_value(event: Event) -> str:
    score = (event.nsm.p + event.nsm.q + event.nsm.r) / 30.0
    text = f"{score:.2f}"
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text


class AgendaView:
    COLUMN_COUNT = 4
    _HEADERS: Sequence[str] = ("x", "y", "z", "nsm")
    _MIN_WIDTHS: Sequence[int] = (
        _MIN_X_WIDTH,
        _MIN_Y_WIDTH,
        _MIN_Z_WIDTH,
        _MIN_NSM_WIDTH,
    )
    _MAX_WIDTHS: Sequence[int] = (
        _MAX_X_WIDTH,
        _MAX_Y_WIDTH,
        _MAX_Z_WIDTH,
        _MAX_NSM_WIDTH,
    )
    _ALIGNMENTS: Sequence[str] = ("right", "right", "right", "right")

    def __init__(self, events: List[Event]):
        self.events = events

    def render(
        self,
        stdscr: "curses.window",
        selected_idx: int,
        scroll: int,
        *,
        expand_all: bool = True,
        selected_col: int = 0,
        row_overrides: set[tuple] | None = None,
    ) -> int:  # type: ignore[name-defined]
        h, w = stdscr.getmaxyx()
        usable_h = h - 1
        usable_w = max(0, w - 1)

        if usable_h <= 0 or usable_w <= 0:
            return (
                0 if not self.events else clamp(scroll, 0, max(0, len(self.events) - 1))
            )

        selected_col = clamp(selected_col, 0, self.COLUMN_COUNT - 1)
        row_overrides = row_overrides or set()

        timestamps = [ev.jtbd.x.strftime(_TIMESTAMP_FMT) for ev in self.events]
        y_values = [ev.jtbd.y for ev in self.events]
        z_values = [ev.jtbd.z for ev in self.events]
        nsm_values = [_format_nsm_value(ev) for ev in self.events]

        column_samples: Sequence[Sequence[str]] = (
            timestamps,
            y_values,
            z_values,
            nsm_values,
        )

        column_lengths: List[int] = []
        for idx, samples in enumerate(column_samples):
            if idx == 1 or idx == 2:
                max_len = max((_max_line_length(val) for val in samples), default=0)
            else:
                max_len = max((len(val) for val in samples), default=0)
            column_lengths.append(max_len)

        widths: List[int] = []
        for idx in range(self.COLUMN_COUNT):
            min_w = self._MIN_WIDTHS[idx]
            max_w = self._MAX_WIDTHS[idx]
            header_len = len(self._HEADERS[idx])
            data_len = column_lengths[idx]
            width = max(min_w, min(max_w, max(header_len, data_len)))
            widths.append(width)

        total_width = sum(widths) + (self.COLUMN_COUNT - 1) * _GAP_WIDTH

        if total_width > usable_w:
            while total_width > usable_w and any(
                cur > mn for cur, mn in zip(widths, self._MIN_WIDTHS)
            ):
                largest_idx = max(range(self.COLUMN_COUNT), key=lambda idx: widths[idx])
                if widths[largest_idx] <= self._MIN_WIDTHS[largest_idx]:
                    break
                widths[largest_idx] -= 1
                total_width -= 1

        if total_width > usable_w:
            idx_iter = 0
            while total_width > usable_w and any(value > 1 for value in widths):
                if widths[idx_iter] > 1:
                    widths[idx_iter] -= 1
                    total_width -= 1
                idx_iter = (idx_iter + 1) % self.COLUMN_COUNT

        if total_width > usable_w and usable_w > 0:
            overflow = total_width - usable_w
            for idx in range(self.COLUMN_COUNT):
                if overflow <= 0:
                    break
                reducible = widths[idx] - 1
                if reducible <= 0:
                    continue
                delta = min(reducible, overflow)
                widths[idx] -= delta
                overflow -= delta
                total_width -= delta

        widths = [max(1, width) for width in widths]
        total_width = sum(widths) + (self.COLUMN_COUNT - 1) * _GAP_WIDTH
        if total_width > usable_w and usable_w > 0:
            return clamp(scroll, 0, max(0, len(self.events) - 1))

        starts: List[int] = []
        current_x = 0
        for width in widths:
            starts.append(current_x)
            current_x += width + _GAP_WIDTH
        tail_width = max(0, usable_w - (starts[-1] + widths[-1]))

        def write(
            y: int,
            x: int,
            width: int,
            text: str,
            attr: int = 0,
            align: str = "left",
        ) -> None:
            if width <= 0 or y < 0 or y >= usable_h:
                return
            if x >= usable_w:
                return
            span = min(width, max(0, usable_w - x))
            if span <= 0:
                return
            try:
                raw = text or ""
                if len(raw) > span:
                    raw = raw[-span:] if align == "right" else raw[:span]
                if align == "right":
                    padded = raw.rjust(span)
                elif align == "center":
                    padded = raw.center(span)
                else:
                    padded = raw.ljust(span)
                stdscr.addnstr(y, x, padded, span, attr)
            except curses.error:
                pass

        header_y = 0
        for idx, header in enumerate(self._HEADERS):
            write(
                header_y,
                starts[idx],
                widths[idx],
                header,
                curses.A_BOLD,
                align=self._ALIGNMENTS[idx],
            )
            if idx < self.COLUMN_COUNT - 1:
                write(
                    header_y,
                    starts[idx] + widths[idx],
                    _GAP_WIDTH,
                    " " * _GAP_WIDTH,
                    curses.A_BOLD,
                )
        if tail_width > 0:
            write(header_y, starts[-1] + widths[-1], tail_width, "", curses.A_BOLD)

        data_top = 1
        data_height = usable_h - 1
        if data_height <= 0:
            return (
                0 if not self.events else clamp(scroll, 0, max(0, len(self.events) - 1))
            )

        if not self.events:
            write(data_top, 0, usable_w, _NO_TASKS_MESSAGE[:usable_w])
            return 0

        rows = []
        for idx, event in enumerate(self.events):
            identity = _event_identity(event)
            if expand_all:
                is_expanded = identity not in row_overrides
            else:
                is_expanded = identity in row_overrides

            y_lines_full = _wrap_text(y_values[idx], widths[1])
            z_lines_full = _wrap_text(z_values[idx], widths[2])
            y_lines = y_lines_full if is_expanded else y_lines_full[:1]
            z_lines = z_lines_full if is_expanded else z_lines_full[:1]
            y_lines = y_lines or [""]
            z_lines = z_lines or [""]

            columns = [
                [timestamps[idx]],
                y_lines,
                z_lines,
                [nsm_values[idx]],
            ]
            height = max(len(lines) for lines in columns)
            rows.append(
                {
                    "identity": identity,
                    "columns": columns,
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
            columns = row["columns"]
            attrs = [
                curses.A_REVERSE if (idx == selected_idx and selected_col == col_idx) else 0
                for col_idx in range(self.COLUMN_COUNT)
            ]

            for line_offset in range(row_lines):
                if y_cursor >= data_bottom:
                    break

                for col_idx in range(self.COLUMN_COUNT):
                    column_lines = columns[col_idx]
                    text = (
                        column_lines[line_offset]
                        if line_offset < len(column_lines)
                        else ""
                    )
                    write(
                        y_cursor,
                        starts[col_idx],
                        widths[col_idx],
                        text,
                        attrs[col_idx],
                        align=self._ALIGNMENTS[col_idx],
                    )
                    if col_idx < self.COLUMN_COUNT - 1:
                        write(
                            y_cursor,
                            starts[col_idx] + widths[col_idx],
                            _GAP_WIDTH,
                            " " * _GAP_WIDTH,
                            attrs[col_idx],
                        )
                if tail_width > 0:
                    write(y_cursor, starts[-1] + widths[-1], tail_width, "", 0)

                y_cursor += 1

            if y_cursor >= data_bottom:
                break

        return scroll

    def move_selection(self, selected_idx: int, delta: int) -> int:
        if not self.events:
            return 0
        return clamp(selected_idx + delta, 0, len(self.events) - 1)

    def jump_to_today(self) -> int:
        if not self.events:
            return 0
        today = datetime.today()
        for idx, ev in enumerate(self.events):
            if ev.jtbd.x >= today:
                return idx
        return len(self.events) - 1

    def clamp_column(self, col: int) -> int:
        return clamp(col, 0, self.COLUMN_COUNT - 1)


__all__ = ["AgendaView"]
