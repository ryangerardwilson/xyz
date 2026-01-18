#!/usr/bin/env python3
"""Orchestrator for tcal."""
from __future__ import annotations

import argparse
import curses
import time
from datetime import date, datetime
from typing import List, Sequence, cast

from config import load_config
from editor import edit_event_via_editor
from keys import (
    KEY_CAP_Q,
    KEY_ESC,
    KEY_H,
    KEY_HELP,
    KEY_I,
    KEY_J,
    KEY_K,
    KEY_L,
    KEY_LEADER,
    KEY_Q,
    KEY_TAB,
    KEY_TODAY,
)
from models import Event, ValidationError
from state import AppState
from store import StorageError, load_events, upsert_event
from ui_base import draw_centered_box, draw_footer, draw_header
from view_agenda import AgendaView
from view_month import MonthView

LEADER_TIMEOUT_MS = 1000
SEEDED_DEFAULT_TIME = "09:00:00"


class Orchestrator:
    """Owns CLI parsing and the curses lifecycle."""

    def __init__(self) -> None:
        self.config = load_config()
        self.state = AppState()
        self.last_tick_ms = 0

    def run(self) -> int:
        return self._run_curses()

    def _run_curses(self) -> int:
        try:
            curses.wrapper(self._curses_main)
        except KeyboardInterrupt:
            return 130
        except curses.error as exc:
            print(f"curses error: {exc}")
            return 1
        return 0

    def _curses_main(self, stdscr: "curses.window") -> None:  # type: ignore[name-defined]
        curses.curs_set(0)
        stdscr.nodelay(True)
        stdscr.timeout(100)
        try:
            curses.start_color()
            curses.use_default_colors()
        except curses.error:
            pass

        # Initial load
        try:
            self.state.events = load_events(self.config.data_csv_path)
            self.state.overlay = "none"
            self.state.overlay_message = ""
        except StorageError as exc:
            self.state.overlay = "error"
            self.state.overlay_message = f"Storage error: {exc}"
            self.state.events = []

        self._draw(stdscr)

        while True:
            ch = stdscr.getch()
            now_ms = int(time.time() * 1000)
            self._maybe_timeout_leader(now_ms)

            if ch in (-1, curses.ERR):
                continue
            if ch in (KEY_Q, KEY_CAP_Q):
                break

            handled = self._handle_key(stdscr, ch)
            if handled:
                self._draw(stdscr)

    # Rendering
    def _draw(self, stdscr: "curses.window") -> None:  # type: ignore[name-defined]
        stdscr.erase()
        header = f"tcal — {self.state.view}"
        draw_header(stdscr, header)

        footer = "q: quit   ?: help   ,: leader   t: today   i: edit/create   Tab: focus (month)"
        draw_footer(stdscr, footer)

        if self.state.view == "agenda":
            view = AgendaView(self.state.events)
            self.state.agenda_scroll = view.render(stdscr, self.state.agenda_index, self.state.agenda_scroll)
        else:
            view = MonthView(self.state.events)
            view.render(
                stdscr,
                self.state.month_selected_date,
                self.state.month_focus,
                self.state.month_event_index,
            )

        if self.state.overlay != "none":
            self._render_overlay(stdscr)

        stdscr.refresh()

    def _render_overlay(self, stdscr: "curses.window") -> None:  # type: ignore[name-defined]
        if self.state.overlay == "help":
            lines = [
                "tcal help",
                "",
                "q           quit",
                "?           toggle this help",
                "t           jump to today",
                ",a / ,m    agenda / month view",
                "hjkl        navigate",
                "Tab         toggle focus (month view)",
                "i           edit selected / create new",
                "",
                "Edits open external editor on temp JSON",
                "datetime format: YYYY-MM-DD HH:MM[:SS]",
                "",
                "Esc to dismiss",
            ]
            draw_centered_box(stdscr, lines)
        elif self.state.overlay in ("error", "message"):
            draw_centered_box(stdscr, [self.state.overlay_message, "", "Press any key to dismiss"])

    # Key handling
    def _handle_key(self, stdscr: "curses.window", ch: int) -> bool:
        # Overlays dismiss on any key (except help which uses Esc as well)
        if self.state.overlay == "help":
            if ch == KEY_ESC:
                self.state.overlay = "none"
                return True
            # Allow other keys to pass to main flow too
        elif self.state.overlay in ("error", "message"):
            self.state.overlay = "none"
            return True

        # Leader handling
        if self.state.leader.active:
            self.state.leader.active = False
            if ch == ord("a"):
                self.state.view = "agenda"
                return True
            if ch == ord("m"):
                self.state.view = "month"
                return True
            if ch == ord("n"):
                return self._edit_or_create(stdscr, force_new=True)
            return True  # unknown leader key just cancels


        if ch == KEY_LEADER:
            self.state.leader.active = True
            self.state.leader.started_at_ms = int(time.time() * 1000)
            return False

        if ch == KEY_HELP:
            self.state.overlay = "help"
            return True

        if ch == KEY_ESC:
            # Cancel overlays/leader
            self.state.overlay = "none"
            self.state.leader.active = False
            return True

        if ch == KEY_TODAY:
            return self._jump_today()

        if ch == KEY_I:
            force_new = self.state.view == "agenda" and not self.state.events
            return self._edit_or_create(stdscr, force_new=force_new)

        # View-specific navigation
        if self.state.view == "agenda":
            return self._handle_agenda_keys(ch)
        else:
            return self._handle_month_keys(ch)

    def _maybe_timeout_leader(self, now_ms: int) -> None:
        if self.state.leader.active and self.state.leader.started_at_ms:
            if now_ms - self.state.leader.started_at_ms > LEADER_TIMEOUT_MS:
                self.state.leader.active = False

    # Agenda behaviors
    def _handle_agenda_keys(self, ch: int) -> bool:
        view = AgendaView(self.state.events)
        if ch == KEY_J:
            self.state.agenda_index = view.move_selection(self.state.agenda_index, +1)
            return True
        if ch == KEY_K:
            self.state.agenda_index = view.move_selection(self.state.agenda_index, -1)
            return True
        if ch == KEY_H:
            return self._agenda_jump_day(-1)
        if ch == KEY_L:
            return self._agenda_jump_day(+1)
        return False

    def _agenda_jump_day(self, direction: int) -> bool:
        if not self.state.events:
            return False
        cur_idx = self.state.agenda_index
        cur_day = self.state.events[cur_idx].datetime.date()
        if direction < 0:
            for idx in range(cur_idx - 1, -1, -1):
                if self.state.events[idx].datetime.date() < cur_day:
                    target_day = self.state.events[idx].datetime.date()
                    first_idx = next(
                        (i for i, ev in enumerate(self.state.events) if ev.datetime.date() == target_day), idx
                    )
                    self.state.agenda_index = first_idx
                    return True
        else:
            for idx in range(cur_idx + 1, len(self.state.events)):
                if self.state.events[idx].datetime.date() > cur_day:
                    self.state.agenda_index = idx
                    return True
        return False

    # Month behaviors
    def _handle_month_keys(self, ch: int) -> bool:
        view = MonthView(self.state.events)
        if self.state.month_focus == "grid":
            if ch == KEY_H:
                self.state.month_selected_date = view.move_day(self.state.month_selected_date, -1)
                self.state.month_event_index = 0
                return True
            if ch == KEY_L:
                self.state.month_selected_date = view.move_day(self.state.month_selected_date, +1)
                self.state.month_event_index = 0
                return True
            if ch == KEY_J:
                self.state.month_selected_date = view.move_week(self.state.month_selected_date, +1)
                self.state.month_event_index = 0
                return True
            if ch == KEY_K:
                self.state.month_selected_date = view.move_week(self.state.month_selected_date, -1)
                self.state.month_event_index = 0
                return True
            if ch == KEY_TAB:
                self.state.month_focus = "events"
                self.state.month_event_index = view.clamp_event_index(
                    self.state.month_selected_date, self.state.month_event_index
                )
                return True
        else:  # focus == events
            if ch == KEY_TAB:
                self.state.month_focus = "grid"
                return True
            if ch == KEY_J:
                self.state.month_event_index = view.clamp_event_index(
                    self.state.month_selected_date, self.state.month_event_index + 1
                )
                return True
            if ch == KEY_K:
                self.state.month_event_index = view.clamp_event_index(
                    self.state.month_selected_date, self.state.month_event_index - 1
                )
                return True
        return False

    # Jump to today
    def _jump_today(self) -> bool:
        today = date.today()
        if self.state.view == "agenda":
            view = AgendaView(self.state.events)
            self.state.agenda_index = view.jump_to_today()
            return True
        else:
            self.state.month_selected_date = today
            self.state.month_event_index = 0
            return True

    # Editing / creating
    def _edit_or_create(self, stdscr: "curses.window", *, force_new: bool = False) -> bool:  # type: ignore[name-defined]
        if self.state.view == "agenda":
            seeds = self._seed_events_for_agenda(force_new=force_new)
            original_allowed = False if force_new else True
        else:
            seeds = self._seed_events_for_month(force_new=force_new)
            original_allowed = True

        if not seeds:
            return False

        # Exit curses before launching editor
        curses.def_prog_mode()
        curses.endwin()
        ok, result = edit_event_via_editor(self.config.editor, seeds)
        curses.reset_prog_mode()
        stdscr.refresh()
        curses.curs_set(0)
        stdscr.nodelay(True)
        stdscr.timeout(100)

        if not ok:
            self._show_overlay(stdscr, str(result), kind="error")
            return True

        updated_events = cast(List[Event], result)
        originals: List[Event] = []
        if original_allowed and self.state.view == "agenda" and self.state.events:
            originals = [self.state.events[self.state.agenda_index]]
        elif self.state.view == "month":
            originals = [e for e in self.state.events if e.datetime.date() == self.state.month_selected_date]

        try:
            new_events = self.state.events
            for idx, ev in enumerate(updated_events):
                original = originals[idx] if idx < len(originals) else None
                new_events = upsert_event(
                    self.config.data_csv_path,
                    new_events,
                    ev,
                    replace_dt=(original is not None, original),
                )
            self.state.events = new_events
            # Rebuild any derived selection indices sensibly
            if self.state.view == "agenda":
                # Move selection to first updated event
                target_dt = updated_events[0].datetime
                for idx, ev in enumerate(self.state.events):
                    if ev.datetime == target_dt:
                        self.state.agenda_index = idx
                        break
            else:
                self.state.month_event_index = 0
        except ValidationError as exc:
            self._show_overlay(stdscr, str(exc), kind="error")
        except StorageError as exc:
            self._show_overlay(stdscr, f"Storage error: {exc}", kind="error")
        return True

    def _seed_events_for_agenda(self, *, force_new: bool = False) -> List[Event]:
        if not force_new and self.state.events and 0 <= self.state.agenda_index < len(self.state.events):
            return [self.state.events[self.state.agenda_index]]
        today = date.today()
        dt_str = f"{today.strftime('%Y-%m-%d')} {SEEDED_DEFAULT_TIME}"
        from models import parse_datetime

        return [Event(datetime=parse_datetime(dt_str), event="", details="")]

    def _seed_events_for_month(self, *, force_new: bool = False) -> List[Event]:
        sel_day = self.state.month_selected_date
        if not force_new:
            evs = [e for e in self.state.events if e.datetime.date() == sel_day]
            if evs:
                return evs
        dt_str = f"{sel_day.strftime('%Y-%m-%d')} {SEEDED_DEFAULT_TIME}"
        from models import parse_datetime

        return [Event(datetime=parse_datetime(dt_str), event="", details="")]

    def _show_overlay(self, stdscr: "curses.window", message: str, kind: str = "error") -> None:  # type: ignore[name-defined]
        self.state.overlay = "error" if kind == "error" else "message"
        self.state.overlay_message = message
        self._draw(stdscr)


__all__ = ["Orchestrator"]
