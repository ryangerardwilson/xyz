#!/usr/bin/env python3
"""Orchestrator for tcal."""

from __future__ import annotations

import curses
import time
from datetime import date, timedelta
from typing import List, cast

from calendar_service import CalendarService, StorageError
from config import load_config
from editor import edit_event_via_editor
from nl_executor import NaturalLanguageExecutor
from openai_client import OpenAIClient, DEFAULT_MODEL as OPENAI_DEFAULT_MODEL

DEFAULT_EDITOR = "vim"

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
    KEY_D,
    KEY_CTRL_H,
    KEY_CTRL_L,
)
from models import Event, ValidationError
from state import AppState
from ui_base import draw_centered_box, draw_footer
from view_agenda import AgendaView
from view_month import MonthView

LEADER_TIMEOUT_MS = 1000
DELETE_TIMEOUT_MS = 600
SEEDED_DEFAULT_TIME = "09:00:00"


class Orchestrator:
    """Owns CLI parsing and the curses lifecycle."""

    def __init__(self) -> None:
        self.config = load_config()
        self.calendar = CalendarService(self.config.data_csv_path)
        self.state = AppState()
        self.last_tick_ms = 0
        self._pending_delete = {
            "active": False,
            "started_at": 0,
            "target_view": "agenda",
        }

    def run(self) -> int:
        return self._run_curses()

    # Natural-language CLI entrypoint
    def handle_nl_cli(self, text: str) -> int:
        if not self.config.openai_api_key:
            print(
                "Missing openai_api_key in config. Please set it in ~/.config/tcal/config.json"
            )
            return 1

        try:
            existing = self.calendar.load_events()
        except StorageError as exc:
            print(f"Storage error: {exc}")
            return 1

        model = self.config.openai_model or OPENAI_DEFAULT_MODEL
        client = OpenAIClient(
            self.config.openai_api_key,
            model=model,
        )
        executor = NaturalLanguageExecutor(client, self.calendar)
        result = executor.execute(text, existing_events=existing)

        print(result.message)
        if result.success and result.events is not None:
            self.state.events = result.events
            return 0
        return 1

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
            self.state.events = self.calendar.load_events()
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
            self._maybe_timeout_delete(now_ms)

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

        footer = "? help"
        draw_footer(stdscr, footer)

        if self.state.view == "agenda":
            view = AgendaView(self.state.events)
            self.state.agenda_scroll = view.render(
                stdscr, self.state.agenda_index, self.state.agenda_scroll
            )
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
                "tcal shortcuts",
                "",
                "q            quit",
                "?            toggle this help",
                "t            jump to today",
                "i            edit/create event",
                "dd           delete selected event",
                "hjkl         navigate (agenda/month)",
                "Ctrl+h/l     month view: prev/next month",
                ",a / ,m      switch agenda / month",
                "Tab          toggle focus (month view)",
                "Esc          dismiss overlays",
            ]
            draw_centered_box(stdscr, lines)
        elif self.state.overlay in ("error", "message"):
            draw_centered_box(
                stdscr, [self.state.overlay_message, "", "Press any key to dismiss"]
            )

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

        handled_delete = self._handle_delete_key(ch)
        if handled_delete is not None:
            return handled_delete

        if ch == KEY_HELP:
            self.state.overlay = "help"
            return True

        if ch == KEY_ESC:
            # Cancel overlays/leader or exit month events focus
            handled = False
            if self.state.view == "month" and self.state.month_focus == "events":
                self.state.month_focus = "grid"
                handled = True
            self.state.overlay = "none"
            self.state.leader.active = False
            self._pending_delete["active"] = False
            return True if handled or self.state.overlay == "none" else False

        if ch == KEY_TODAY:
            return self._jump_today()

        if ch == KEY_I:
            if self.state.view == "agenda":
                force_new = not self.state.events
                return self._edit_or_create(stdscr, force_new=force_new)
            elif (
                self.state.view == "month"
                and self.state.month_focus == "events"
                and self._month_events_for_selected_date()
            ):
                return self._edit_or_create(stdscr, force_new=False)
            else:
                return False

        # View-specific navigation
        if self.state.view == "agenda":
            return self._handle_agenda_keys(ch)
        else:
            return self._handle_month_keys(ch)

    def _maybe_timeout_leader(self, now_ms: int) -> None:
        if self.state.leader.active and self.state.leader.started_at_ms:
            if now_ms - self.state.leader.started_at_ms > LEADER_TIMEOUT_MS:
                self.state.leader.active = False

    def _maybe_timeout_delete(self, now_ms: int) -> None:
        if self._pending_delete["active"]:
            if now_ms - self._pending_delete["started_at"] > DELETE_TIMEOUT_MS:
                self._pending_delete["active"] = False

    def _handle_delete_key(self, ch: int) -> bool | None:
        if ch != KEY_D:
            self._pending_delete["active"] = False
            return None

        now_ms = int(time.time() * 1000)
        if (
            self._pending_delete["active"]
            and now_ms - self._pending_delete["started_at"] <= DELETE_TIMEOUT_MS
        ):
            # Second 'd'
            self._pending_delete["active"] = False
            return self._perform_delete()

        # First 'd'
        self._pending_delete["active"] = True
        self._pending_delete["started_at"] = now_ms
        self._pending_delete["target_view"] = self.state.view
        return False

    def _perform_delete(self) -> bool:
        if self.state.view == "agenda":
            if not self.state.events:
                return False
            target = self.state.events[self.state.agenda_index]
        elif self.state.view == "month" and self.state.month_focus == "events":
            month_events = self._month_events_for_selected_date()
            if not month_events:
                return False
            idx = min(self.state.month_event_index, len(month_events) - 1)
            target = month_events[idx]
        else:
            return False

        try:
            new_events = self.calendar.delete_event(self.state.events, target)
        except StorageError as exc:
            self.state.overlay = "error"
            self.state.overlay_message = f"Storage error: {exc}"
            return True

        self.state.events = new_events
        if self.state.view == "agenda":
            self.state.agenda_index = min(self.state.agenda_index, len(new_events) - 1)
            if self.state.agenda_index < 0:
                self.state.agenda_index = 0
        else:
            month_events = self._month_events_for_selected_date()
            self.state.month_event_index = min(
                self.state.month_event_index, max(len(month_events) - 1, 0)
            )
        return True

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
                        (
                            i
                            for i, ev in enumerate(self.state.events)
                            if ev.datetime.date() == target_day
                        ),
                        idx,
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
            if ch == KEY_CTRL_H:
                self.state.month_selected_date = view.move_month(
                    self.state.month_selected_date, -1
                )
                self.state.month_event_index = 0
                return True
            if ch == KEY_CTRL_L:
                self.state.month_selected_date = view.move_month(
                    self.state.month_selected_date, +1
                )
                self.state.month_event_index = 0
                return True
            if ch == KEY_H:
                self.state.month_selected_date = view.move_day(
                    self.state.month_selected_date, -1
                )
                self.state.month_event_index = 0
                return True
            if ch == KEY_L:
                self.state.month_selected_date = view.move_day(
                    self.state.month_selected_date, +1
                )
                self.state.month_event_index = 0
                return True
            if ch == KEY_J:
                self.state.month_selected_date = view.move_week(
                    self.state.month_selected_date, +1
                )
                self.state.month_event_index = 0
                return True
            if ch == KEY_K:
                self.state.month_selected_date = view.move_week(
                    self.state.month_selected_date, -1
                )
                self.state.month_event_index = 0
                return True
            if ch == KEY_TAB:
                if self._month_events_for_selected_date():
                    self.state.month_focus = "events"
                    self.state.month_event_index = view.clamp_event_index(
                        self.state.month_selected_date, self.state.month_event_index
                    )
                    return True
                return False
        else:  # focus == events
            if ch == KEY_TAB:
                return False
            if ch == KEY_CTRL_H:
                self.state.month_selected_date = view.move_month(
                    self.state.month_selected_date, -1
                )
                self.state.month_event_index = 0
                if not view.events_by_date.get(self.state.month_selected_date):
                    self.state.month_focus = "grid"
                return True
            if ch == KEY_CTRL_L:
                self.state.month_selected_date = view.move_month(
                    self.state.month_selected_date, +1
                )
                self.state.month_event_index = 0
                if not view.events_by_date.get(self.state.month_selected_date):
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
    def _edit_or_create(
        self, stdscr: "curses.window", *, force_new: bool = False
    ) -> bool:  # type: ignore[name-defined]
        single_event_payload = False
        if self.state.view == "agenda":
            seeds = self._seed_events_for_agenda(force_new=force_new)
            allow_overwrite = not force_new and bool(self.state.events)
            originals_source = (
                [self.state.events[self.state.agenda_index]]
                if allow_overwrite and 0 <= self.state.agenda_index < len(self.state.events)
                else []
            )
            single_event_payload = len(seeds) == 1
        else:
            has_existing = bool(self._month_events_for_selected_date())
            select_single = not force_new and self.state.month_focus == "events" and has_existing
            seeds = self._seed_events_for_month(
                force_new=force_new, selected_only=select_single
            )
            allow_overwrite = not force_new and has_existing
            month_events = self._month_events_for_selected_date()
            if select_single and 0 <= self.state.month_event_index < len(month_events):
                originals_source = [month_events[self.state.month_event_index]]
            elif allow_overwrite:
                originals_source = month_events
            else:
                originals_source = []
            single_event_payload = len(seeds) == 1

        if not seeds:
            return False

        payload: Event | List[Event]
        if single_event_payload:
            payload = seeds[0]
        else:
            payload = seeds

        # Exit curses before launching editor
        curses.def_prog_mode()
        curses.endwin()
        ok, result = edit_event_via_editor(DEFAULT_EDITOR, payload)
        curses.reset_prog_mode()
        stdscr.refresh()
        curses.curs_set(0)
        stdscr.nodelay(True)
        stdscr.timeout(100)

        if not ok:
            self._show_overlay(stdscr, str(result), kind="error")
            return True

        updated_events = cast(List[Event], result)
        originals: List[Event] = originals_source if allow_overwrite else []

        try:
            new_events = self.state.events
            for idx, ev in enumerate(updated_events):
                original = originals[idx] if idx < len(originals) else None
                new_events = self.calendar.upsert_event(
                    new_events,
                    ev,
                    replace_dt=(original is not None, original),
                )
            self.state.events = new_events
            self._pending_delete["active"] = False
            # Rebuild any derived selection indices sensibly
            if self.state.view == "agenda":
                target_dt = updated_events[0].datetime
                for idx, ev in enumerate(self.state.events):
                    if (
                        ev.datetime == target_dt
                        and ev.event == updated_events[0].event
                        and ev.details == updated_events[0].details
                    ):
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
        if (
            not force_new
            and self.state.events
            and 0 <= self.state.agenda_index < len(self.state.events)
        ):
            return [self.state.events[self.state.agenda_index]]
        today = date.today()
        dt_str = f"{today.strftime('%Y-%m-%d')} {SEEDED_DEFAULT_TIME}"
        from models import parse_datetime

        return [Event(datetime=parse_datetime(dt_str), event="", details="")]

    def _seed_events_for_month(
        self,
        *,
        force_new: bool = False,
        selected_only: bool = False,
    ) -> List[Event]:
        sel_day = self.state.month_selected_date
        if not force_new:
            evs = self._month_events_for_selected_date()
            if evs:
                if selected_only and 0 <= self.state.month_event_index < len(evs):
                    return [evs[self.state.month_event_index]]
                return evs
        dt_str = f"{sel_day.strftime('%Y-%m-%d')} {SEEDED_DEFAULT_TIME}"
        from models import parse_datetime

        return [Event(datetime=parse_datetime(dt_str), event="", details="")]

    def _month_events_for_selected_date(self) -> List[Event]:
        sel_day = self.state.month_selected_date
        return [e for e in self.state.events if e.datetime.date() == sel_day]

    def _show_overlay(
        self, stdscr: "curses.window", message: str, kind: str = "error"
    ) -> None:  # type: ignore[name-defined]
        self.state.overlay = "error" if kind == "error" else "message"
        self.state.overlay_message = message
        self._draw(stdscr)


__all__ = ["Orchestrator"]
