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
        stdscr: "curses._CursesWindow",  # type: ignore[name-defined]
        selected_date: date,
        focus: str,
        selected_event_idx: int,
    ) -> None:
        h, w = stdscr.getmaxyx()
        body_h = h - 2
        body_w = w

        # Reserve right pane ~40 cols for events
        right_w = max(30, min(50, body_w // 3))
        grid_w = body_w - right_w - 1

        # Draw grid on left
        self._draw_grid(stdscr, 1, 0, body_h - 1, grid_w, selected_date)

        # Draw events pane on right
        self._draw_events_pane(stdscr, 1, grid_w + 1, body_h - 1, right_w, selected_date, focus, selected_event_idx)

    def _draw_grid(self, stdscr: "curses._CursesWindow", y: int, x: int, h: int, w: int, selected_date: date) -> None:  # type: ignore[name-defined]
        cal = calendar.Calendar(firstweekday=0)
        year, month = selected_date.year, selected_date.month
        weeks = cal.monthdatescalendar(year, month)
        today = date.today()

        cell_w = max(8, w // 7)
        for row_idx, week in enumerate(weeks):
            row_y = y + row_idx * 2
            if row_y >= y + h:
                break
            for col_idx, day in enumerate(week):
                col_x = x + col_idx * cell_w
                label = f"{day.day:2d}"
                events_count = len(self.events_by_date.get(day, []))
                suffix = f" ({events_count})" if events_count else ""
                text = (label + suffix)[: cell_w - 1].ljust(cell_w - 1)

                attr = 0
                if day == today:
                    attr |= curses.A_BOLD
                if day.month != month:
                    attr |= curses.A_DIM
                if day == selected_date:
                    attr |= curses.A_REVERSE

                stdscr.addnstr(row_y, col_x, text, cell_w - 1, attr)

    def _draw_events_pane(
        self,
        stdscr: "curses._CursesWindow",  # type: ignore[name-defined]
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
        stdscr.addnstr(y, x, title.ljust(w), w, curses.A_BOLD)

        if not evs:
            stdscr.addnstr(y + 1, x, "(none) — press i to create".ljust(w), w, curses.A_DIM)
            return

        body_h = h - 1
        selected_event_idx = clamp(selected_event_idx, 0, max(0, len(evs) - 1))
        for idx in range(min(body_h, len(evs))):
            ev = evs[idx]
            ts = ev.datetime.strftime("%H:%M")
            line = f"{ts} {ev.event}"[: w - 1].ljust(w - 1)
            attr = curses.A_REVERSE if (focus == "events" and idx == selected_event_idx) else 0
            stdscr.addnstr(y + 1 + idx, x, line, w - 1, attr)

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
