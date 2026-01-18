#!/usr/bin/env python3
"""Agenda view rendering and interactions."""
from __future__ import annotations

import curses
from datetime import datetime
from typing import List

from models import Event
from ui_base import clamp


class AgendaView:
    def __init__(self, events: List[Event]):
        self.events = events

    def render(self, stdscr: "curses._CursesWindow", selected_idx: int, scroll: int) -> None:  # type: ignore[name-defined]
        h, w = stdscr.getmaxyx()
        body_h = h - 2  # header/footer handled by orchestrator

        lines: List[str] = []
        for ev in self.events:
            ts = ev.datetime.strftime("%Y-%m-%d %H:%M")
            lines.append(f"{ts}  {ev.event}")
        if not lines:
            lines = ["No events yet. Press i to create."]

        # Clamp selection and scroll
        selected_idx = clamp(selected_idx, 0, max(0, len(lines) - 1))
        scroll = clamp(scroll, 0, max(0, len(lines) - body_h))

        for idx in range(body_h):
            line_idx = scroll + idx
            if line_idx >= len(lines):
                break
            line = lines[line_idx]
            attr = curses.A_REVERSE if line_idx == selected_idx and self.events else 0
            stdscr.addnstr(1 + idx, 0, line.ljust(w), w, attr)

    def move_selection(self, selected_idx: int, delta: int) -> int:
        if not self.events:
            return 0
        return clamp(selected_idx + delta, 0, len(self.events) - 1)

    def jump_to_today(self) -> int:
        if not self.events:
            return 0
        today = datetime.today()
        for idx, ev in enumerate(self.events):
            if ev.datetime >= today:
                return idx
        return len(self.events) - 1


__all__ = ["AgendaView"]
