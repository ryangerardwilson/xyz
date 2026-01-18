#!/usr/bin/env python3
"""Month view rendering and interactions."""

from __future__ import annotations

import calendar
import curses
from datetime import date, timedelta
from typing import Dict, List

from models import Event
from ui_base import clamp


class MonthView:
    def __init__(self, events: List[Event]):
        self.events = events
        self.events_by_date = self._group_by_date(events)

    @staticmethod
    def _group_by_date(events: List[Event]) -> Dict[date, List[Event]]:
        out: Dict[date, List[Event]] = {}
        for ev in events:
            d = ev.datetime.date()
            out.setdefault(d, []).append(ev)
        for evs in out.values():
            evs.sort(key=lambda e: e.datetime)
        return out

    def render(
        self,
        stdscr: "curses.window",  # type: ignore[name-defined]
        selected_date: date,
        focus: str,
        selected_event_idx: int,
    ) -> None:
        h, w = stdscr.getmaxyx()
        body_h = h - 1
        body_w = w

        if body_h <= 0 or body_w <= 0:
            return

        title = f"{calendar.month_name[selected_date.month]}, {selected_date.year}"
        stdscr.addnstr(
            0, 0, title[: max(0, body_w - 1)], max(0, body_w - 1), 0
        )

        content_top = 2  # blank line between title and grid
        available_h = body_h - content_top
        if available_h <= 0:
            return

        grid_needed_rows = self._grid_required_rows(selected_date) + 1  # include header row
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
            events_start = content_top + grid_rows + 1  # blank line between grid and events
            self._draw_events_pane(
                stdscr,
                events_start,
                0,
                events_rows,
                body_w,
                selected_date,
                focus,
                selected_event_idx,
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
    ) -> None:
        evs = self.events_by_date.get(selected_date, [])
        if not evs:
            return

        title = f"Events {selected_date.isoformat()}"
        usable_w = max(0, w - 1)
        stdscr.addnstr(y, x, title[:usable_w].ljust(usable_w), usable_w, curses.A_BOLD)

        body_h = h - 1
        if usable_w == 0 or body_h <= 0:
            return
        selected_event_idx = clamp(selected_event_idx, 0, max(0, len(evs) - 1))
        for idx in range(min(body_h, len(evs))):
            ev = evs[idx]
            ts = ev.datetime.strftime("%H:%M")
            line = f"{ts} {ev.event}"[:usable_w].ljust(usable_w)
            attr = (
                curses.A_REVERSE
                if (focus == "events" and idx == selected_event_idx)
                else 0
            )
            stdscr.addnstr(y + 1 + idx, x, line, usable_w, attr)

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
