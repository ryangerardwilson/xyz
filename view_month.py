#!/usr/bin/env python3
"""Month view rendering and interactions."""
from __future__ import annotations

import calendar
import curses
from datetime import date, datetime, timedelta
from typing import Dict, List, Tuple

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
        stdscr.addnstr(0, 0, title[: max(0, body_w - 1)], max(0, body_w - 1), curses.A_BOLD)

        available_h = body_h - 1
        if available_h <= 0:
            return

        grid_needed_rows = self._grid_required_rows(selected_date)
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
            self._draw_grid(stdscr, 1, 0, grid_rows, body_w, selected_date)
        if events_rows > 0:
            self._draw_events_pane(
                stdscr,
                1 + grid_rows,
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

    def _draw_grid(self, stdscr: "curses.window", y: int, x: int, h: int, w: int, selected_date: date) -> None:  # type: ignore[name-defined]
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

        for row_idx, week in enumerate(weeks):
            row_y = y + row_idx
            if row_y >= y + h:
                break
            for col_idx, day in enumerate(week):
                col_x = grid_x + col_idx * cell_w
                label = f"{day.day:2d}"
                events_count = len(self.events_by_date.get(day, []))
                show_suffix = events_count and cell_w >= 8
                suffix = f" ({events_count})" if show_suffix else ""
                text = f"{label}{suffix}"[: cell_w]

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
        title = f"Events {selected_date.isoformat()}"
        usable_w = max(0, w - 1)
        stdscr.addnstr(y, x, title[:usable_w].ljust(usable_w), usable_w, curses.A_BOLD)

        if not evs:
            stdscr.addnstr(y + 1, x, "(none) — press i to create"[:usable_w].ljust(usable_w), usable_w, curses.A_DIM)
            return

        body_h = h - 1
        if usable_w == 0 or body_h <= 0:
            return
        selected_event_idx = clamp(selected_event_idx, 0, max(0, len(evs) - 1))
        for idx in range(min(body_h, len(evs))):
            ev = evs[idx]
            ts = ev.datetime.strftime("%H:%M")
            line = f"{ts} {ev.event}"[:usable_w].ljust(usable_w)
            attr = curses.A_REVERSE if (focus == "events" and idx == selected_event_idx) else 0
            stdscr.addnstr(y + 1 + idx, x, line, usable_w, attr)

    def move_day(self, selected_date: date, delta_days: int) -> date:
        return selected_date + timedelta(days=delta_days)

    def move_week(self, selected_date: date, delta_weeks: int) -> date:
        return selected_date + timedelta(days=7 * delta_weeks)

    def clamp_event_index(self, selected_date: date, idx: int) -> int:
        evs = self.events_by_date.get(selected_date, [])
        if not evs:
            return 0
        return clamp(idx, 0, len(evs) - 1)


__all__ = ["MonthView"]
