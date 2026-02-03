#!/usr/bin/env python3
"""Month view rendering and interactions."""

from __future__ import annotations

import calendar
import curses
import textwrap
from datetime import date, datetime, timedelta
from typing import Dict, List, Set, Tuple

from models import Event
from ui_base import clamp


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


def _event_identity(event: Event) -> Tuple[str, datetime, str, str, float, float, float]:
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


class MonthView:
    EVENT_COLUMN_COUNT = 4

    def __init__(self, events: List[Event]):
        self.events = events
        self.events_by_date = self._group_by_date(events)

    @staticmethod
    def _group_by_date(events: List[Event]) -> Dict[date, List[Event]]:
        out: Dict[date, List[Event]] = {}
        for ev in events:
            d = ev.jtbd.x.date()
            out.setdefault(d, []).append(ev)
        for evs in out.values():
            evs.sort(key=lambda e: e.jtbd.x)
        return out

    def render(
        self,
        stdscr: "curses.window",  # type: ignore[name-defined]
        selected_date: date,
        focus: str,
        selected_event_idx: int,
        selected_col: int,
        *,
        expand_all: bool,
        row_overrides: Set[Tuple[str, datetime, str, str, float, float, float]],
        bucket_label: str,
    ) -> None:
        h, w = stdscr.getmaxyx()
        body_h = h - 1
        body_w = w

        if body_h <= 0 or body_w <= 0:
            return

        title = f"{calendar.month_name[selected_date.month]}, {selected_date.year}"
        stdscr.addnstr(0, 0, title[: max(0, body_w - 1)], max(0, body_w - 1), 0)

        content_top = 2  # blank line between title and grid
        available_h = body_h - content_top
        if available_h <= 0:
            return

        grid_needed_rows = (
            self._grid_required_rows(selected_date) + 1
        )  # include header row
        min_events_rows = 3 if available_h >= 3 else available_h

        grid_rows = min(grid_needed_rows, max(available_h - min_events_rows, 0))
        events_rows = available_h - grid_rows

        if events_rows < min_events_rows and available_h >= min_events_rows:
            events_rows = min_events_rows
            grid_rows = max(available_h - events_rows, 0)

        if events_rows <= 0:
            events_rows = min(available_h, min_events_rows)
            grid_rows = max(available_h - events_rows, 0)

        if grid_rows > 0:
            self._draw_weekday_header(stdscr, content_top, 0, body_w)
            self._draw_grid(
                stdscr,
                content_top + 1,
                0,
                grid_rows - 1,
                body_w,
                selected_date,
            )
        if events_rows > 0:
            events_start = (
                content_top + grid_rows + 1
            )  # blank line between grid and events
            self._draw_events_pane(
                stdscr,
                events_start,
                0,
                events_rows,
                body_w,
                selected_date,
                focus,
                selected_event_idx,
                selected_col,
                expand_all,
                row_overrides,
                bucket_label,
            )

    def _grid_required_rows(self, selected_date: date) -> int:
        cal = calendar.Calendar(firstweekday=0)
        year, month = selected_date.year, selected_date.month
        weeks = cal.monthdatescalendar(year, month)
        return len(weeks)

    def _draw_weekday_header(
        self,
        stdscr: "curses.window",
        y: int,
        x: int,
        w: int,
    ) -> None:
        weekdays = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        usable_w = w
        if usable_w <= 0:
            return
        default_cell_w = 7
        min_cell_w = 4
        cell_w = default_cell_w
        grid_w = cell_w * 7
        if grid_w > w:
            cell_w = max(min_cell_w, w // 7)
        start_x = x
        for idx, name in enumerate(weekdays):
            col_x = start_x + idx * cell_w
            stdscr.addnstr(y, col_x, name[:cell_w].ljust(cell_w), cell_w, curses.A_DIM)

    def _draw_grid(
        self,
        stdscr: "curses.window",
        y: int,
        x: int,
        h: int,
        w: int,
        selected_date: date,
    ) -> None:  # type: ignore[name-defined]
        cal = calendar.Calendar(firstweekday=0)
        year, month = selected_date.year, selected_date.month
        weeks = cal.monthdatescalendar(year, month)
        today = date.today()

        default_cell_w = 7
        min_cell_w = 4
        cell_w = default_cell_w
        grid_w = cell_w * 7
        if grid_w > w:
            cell_w = max(min_cell_w, w // 7)
            grid_w = cell_w * 7
        grid_x = x

        visible_weeks = weeks[:h]

        for row_idx, week in enumerate(visible_weeks):
            row_y = y + row_idx
            for col_idx, day in enumerate(week):
                col_x = grid_x + col_idx * cell_w
                label = f"{day.day:2d}"
                events_count = len(self.events_by_date.get(day, []))
                show_suffix = events_count and cell_w >= 7
                count_display = min(events_count, 99)
                suffix = f"({count_display})" if show_suffix else ""
                text = f"{label}{suffix}"[:cell_w]

                attr = 0
                if day == today:
                    attr |= curses.A_BOLD
                if day.month != month:
                    attr |= curses.A_DIM
                if day == selected_date:
                    attr |= curses.A_REVERSE

                stdscr.addnstr(row_y, col_x, text, cell_w, attr)

    def _draw_events_pane(
        self,
        stdscr: "curses.window",  # type: ignore[name-defined]
        y: int,
        x: int,
        h: int,
        w: int,
        selected_date: date,
        focus: str,
        selected_event_idx: int,
        selected_col: int,
        expand_all: bool,
        row_overrides: Set[Tuple[str, datetime, str, str, float, float, float]],
        bucket_label: str,
    ) -> None:
        events = self.events_by_date.get(selected_date, [])
        selected_col = clamp(selected_col, 0, 5)
        usable_w = max(0, w - 1)

        body_h = h
        if usable_w <= 0 or body_h <= 0:
            return
        if not events:
            return

        headers = ("x", "y", "z", "nsm")
        min_widths = (5, 6, 6, 6)
        max_widths = (12, 60, 40, 12)
        alignments = ("right", "right", "right", "right")
        gap = 1

        timestamps = [ev.jtbd.x.strftime("%H:%M") for ev in events]
        y_values = [ev.jtbd.y for ev in events]
        z_values = [ev.jtbd.z for ev in events]
        nsm_values = [_format_nsm_value(ev) for ev in events]

        column_samples = (
            timestamps,
            y_values,
            z_values,
            nsm_values,
        )

        widths: List[int] = []
        for idx, samples in enumerate(column_samples):
            if idx in (1, 2):
                data_len = max((_max_line_length(val) for val in samples), default=0)
            else:
                data_len = max((len(val) for val in samples), default=0)
            width = max(
                min_widths[idx],
                min(max_widths[idx], max(len(headers[idx]), data_len)),
            )
            widths.append(width)

        total_width = sum(widths) + (len(headers) - 1) * gap

        if total_width > usable_w:
            while total_width > usable_w and any(
                cur > mn for cur, mn in zip(widths, min_widths)
            ):
                largest_idx = max(range(len(headers)), key=lambda idx: widths[idx])
                if widths[largest_idx] <= min_widths[largest_idx]:
                    break
                widths[largest_idx] -= 1
                total_width -= 1

        if total_width > usable_w:
            idx_iter = 0
            while total_width > usable_w and any(value > 1 for value in widths):
                if widths[idx_iter] > 1:
                    widths[idx_iter] -= 1
                    total_width -= 1
                idx_iter = (idx_iter + 1) % len(headers)

        if total_width > usable_w and usable_w > 0:
            overflow = total_width - usable_w
            for idx in range(len(headers)):
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
        total_width = sum(widths) + (len(headers) - 1) * gap
        if total_width > usable_w and usable_w > 0:
            return

        starts: List[int] = []
        current_x = x
        for width in widths:
            starts.append(current_x)
            current_x += width + gap
        tail_width = max(0, usable_w - (starts[-1] + widths[-1] - x))

        def write(
            row: int,
            col: int,
            width: int,
            text: str,
            attr: int = 0,
            align: str = "left",
        ) -> None:
            if width <= 0:
                return
            try:
                raw = text or ""
                if len(raw) > width:
                    raw = raw[-width:] if align == "right" else raw[:width]
                if align == "right":
                    padded = raw.rjust(width)
                elif align == "center":
                    padded = raw.center(width)
                else:
                    padded = raw.ljust(width)
                stdscr.addnstr(row, col, padded, width, attr)
            except curses.error:
                pass

        header_y = y
        for idx, header in enumerate(headers):
            write(
                header_y,
                starts[idx],
                widths[idx],
                header,
                curses.A_BOLD,
                align=alignments[idx],
            )
            if idx < len(headers) - 1:
                write(
                    header_y,
                    starts[idx] + widths[idx],
                    gap,
                    " " * gap,
                    curses.A_BOLD,
                )
        if tail_width > 0:
            write(header_y, starts[-1] + widths[-1], tail_width, "", curses.A_BOLD)

        data_top = header_y + 1
        data_height = body_h - 1
        if data_height <= 0:
            return

        rows = []
        for idx, event in enumerate(events):
            identity = _event_identity(event)
            if expand_all:
                expanded = identity not in row_overrides
            else:
                expanded = identity in row_overrides

            y_lines_full = _wrap_text(y_values[idx], widths[1])
            z_lines_full = _wrap_text(z_values[idx], widths[2])
            y_lines = y_lines_full if expanded else y_lines_full[:1]
            z_lines = z_lines_full if expanded else z_lines_full[:1]
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
        selected_event_idx = clamp(selected_event_idx, 0, total_rows - 1)
        row_heights = [row["height"] for row in rows]

        def compute_visible(start: int) -> List[int]:
            start = max(0, start)
            used = 0
            visible: List[int] = []
            idx = start
            while idx < total_rows:
                height = row_heights[idx]
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

        start_idx = 0
        visible_indices = compute_visible(start_idx)
        while selected_event_idx not in visible_indices and start_idx < total_rows - 1:
            start_idx += 1
            visible_indices = compute_visible(start_idx)

        y_cursor = data_top
        for idx in visible_indices:
            row = rows[idx]
            row_lines = row["height"]
            columns = row["columns"]
            is_active_row = focus == "events" and idx == selected_event_idx
            attrs = [
                curses.A_REVERSE if (is_active_row and selected_col == col_idx) else 0
                for col_idx in range(len(headers))
            ]
            for line_offset in range(row_lines):
                if y_cursor >= data_top + data_height:
                    break
                for col_idx in range(len(headers)):
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
                        align=alignments[col_idx],
                    )
                    if col_idx < len(headers) - 1:
                        write(
                            y_cursor,
                            starts[col_idx] + widths[col_idx],
                            gap,
                            " " * gap,
                            attrs[col_idx],
                        )
                if tail_width > 0:
                    write(y_cursor, starts[-1] + widths[-1], tail_width, "", 0)
                y_cursor += 1
            if y_cursor >= data_top + data_height:
                break

    def move_day(self, selected_date: date, delta_days: int) -> date:
        return selected_date + timedelta(days=delta_days)

    def move_week(self, selected_date: date, delta_weeks: int) -> date:
        return selected_date + timedelta(days=7 * delta_weeks)

    def move_month(self, selected_date: date, delta_months: int) -> date:
        year = selected_date.year + ((selected_date.month - 1 + delta_months) // 12)
        month = (selected_date.month - 1 + delta_months) % 12 + 1
        day = selected_date.day
        # Clamp day to end of target month
        _, max_day = calendar.monthrange(year, month)
        day = min(day, max_day)
        return date(year, month, day)

    def clamp_event_index(self, selected_date: date, idx: int) -> int:
        evs = self.events_by_date.get(selected_date, [])
        if not evs:
            return 0
        return clamp(idx, 0, len(evs) - 1)


__all__ = ["MonthView"]
