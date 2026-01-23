#!/usr/bin/env python3
"""Orchestrator for xyz."""

from __future__ import annotations

import curses
import json
import os
import shlex
import subprocess
import tempfile
import time
from pathlib import Path
from datetime import date
from typing import List, cast

from calendar_service import CalendarService, StorageError
from config import load_config
from editor import edit_event_via_editor
from keys import (
    KEY_A,
    KEY_CAP_Q,
    KEY_CTRL_H,
    KEY_CTRL_J,
    KEY_CTRL_K,
    KEY_CTRL_L,
    KEY_D,
    KEY_ESC,
    KEY_H,
    KEY_HELP,
    KEY_I,
    KEY_J,
    KEY_K,
    KEY_L,
    KEY_LEADER,
    KEY_N,
    KEY_Q,
    KEY_TAB,
    KEY_TODAY,
)
from models import (
    DATETIME_FMT,
    Event,
    ValidationError,
    normalize_event_payload,
    parse_datetime,
    event_to_jsonable,
    BUCKETS,
    BucketName,
    Coordinates,
    DEFAULT_BUCKET,
    ALL_BUCKET,
)
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

    def handle_structured_cli(
        self, bucket_str: str, x_str: str, y_str: str, z_str: str
    ) -> int:
        payload = {
            "bucket": bucket_str,
            "coordinates": {"x": x_str, "y": y_str, "z": z_str},
        }
        try:
            event = normalize_event_payload(payload)
        except ValidationError as exc:
            print(str(exc))
            return 1

        try:
            existing = self.calendar.load_events()
            updated = self.calendar.upsert_event(existing, event)
        except (ValidationError, StorageError) as exc:
            print(str(exc))
            return 1

        print(json.dumps(event_to_jsonable(event), indent=2))
        self.state.events = updated
        self._prune_row_overrides()
        return 0

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
            self._prune_row_overrides()
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

        footer = "? help — x=trigger y=outcome z=impact"
        footer = f"{footer}  |  bucket: {self.state.agenda_bucket_filter}"
        if self.state.view == "month":
            focus_label = (
                "focus:list" if self.state.month_focus == "events" else "focus:month"
            )
            footer = f"{footer}  |  {focus_label}"
        if self.state.leader.active:
            leader_seq = f",{self.state.leader.sequence}"
            footer = f"{footer}  |  {leader_seq}"
        draw_footer(stdscr, footer)

        if self.state.view == "agenda":
            visible_events = self._visible_agenda_events()
            self._ensure_agenda_index_bounds(len(visible_events))
            view = AgendaView(visible_events)
            self.state.agenda_scroll = view.render(
                stdscr,
                self.state.agenda_index,
                self.state.agenda_scroll,
                expand_all=self.state.agenda_expand_all,
                selected_col=self.state.agenda_col,
                row_overrides=self.state.agenda_row_overrides,
            )
        else:
            filtered_events = self._bucket_filtered_events()
            view = MonthView(filtered_events)
            self.state.month_event_index = view.clamp_event_index(
                self.state.month_selected_date, self.state.month_event_index
            )
            self.state.month_event_col = max(0, min(self.state.month_event_col, 2))
            view.render(
                stdscr,
                self.state.month_selected_date,
                self.state.month_focus,
                self.state.month_event_index,
                self.state.month_event_col,
                expand_all=self.state.agenda_expand_all,
                row_overrides=self.state.agenda_row_overrides,
                bucket_label=self.state.agenda_bucket_filter,
            )

        if self.state.overlay != "none":
            self._render_overlay(stdscr)

        stdscr.refresh()

    def _render_overlay(self, stdscr: "curses.window") -> None:  # type: ignore[name-defined]
        if self.state.overlay == "help":
            lines = [
                "xyz shortcuts",
                "",
                "q            quit",
                "?            toggle this help",
                "t            jump to today",
                "i            edit/create event",
                "dd           delete selected event",
                "hjkl         navigate (agenda/month)",
                "B            agenda: edit bucket of selected task",
                ",xr          agenda: toggle expand/collapse current row",
                "Ctrl+h/l     month view: prev/next month",
                "Ctrl+j/k     month view: next/prev year",
                "a            toggle agenda/month",
                "Tab          cycle buckets (agenda & month)",
                "Enter        month view: move focus grid ↔ tasks",
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
            leader_handled = self._handle_leader_input(ch)
            if leader_handled is not None:
                return leader_handled

        if ch == KEY_LEADER:
            self.state.leader.active = True
            self.state.leader.sequence = ""
            self.state.leader.started_at_ms = int(time.time() * 1000)
            return True

        if ch == KEY_TAB:
            self._cycle_agenda_bucket()
            return True

        if ch == KEY_N:
            return self._edit_or_create(stdscr, force_new=True)

        if ch == KEY_A:
            self._toggle_view()
            return True

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
            self.state.leader.sequence = ""
            self.state.leader.started_at_ms = None
            self._pending_delete["active"] = False
            return True if handled or self.state.overlay == "none" else False

        if ch == KEY_TODAY:
            return self._jump_today()

        if ch == KEY_I:
            if self.state.view == "agenda":
                visible = self._visible_agenda_events()
                if not visible:
                    return self._edit_or_create(stdscr, force_new=True)
                return self._edit_agenda_cell(stdscr)
            elif self.state.view == "month" and self.state.month_focus == "events":
                if not self._month_events_for_selected_date():
                    return self._edit_or_create(stdscr, force_new=True)
                return self._edit_month_cell(stdscr)
            else:
                return False

        if ch == ord("B"):
            if self.state.view == "agenda":
                return self._edit_agenda_bucket(stdscr)
            if self.state.view == "month" and self.state.month_focus == "events":
                return self._edit_month_bucket(stdscr)
            return False

        # View-specific navigation
        if self.state.view == "agenda":
            return self._handle_agenda_keys(ch)
        else:
            return self._handle_month_keys(ch)

    def _toggle_view(self) -> None:
        self.state.leader.active = False
        self.state.leader.started_at_ms = None
        self.state.leader.sequence = ""
        if self.state.view == "agenda":
            self.state.view = "month"
            self.state.month_focus = "grid"
            self.state.month_event_index = 0
        else:
            self.state.view = "agenda"
            self._ensure_agenda_index_bounds(len(self._visible_agenda_events()))

    def _maybe_timeout_leader(self, now_ms: int) -> None:
        if self.state.leader.active and self.state.leader.started_at_ms:
            if now_ms - self.state.leader.started_at_ms > LEADER_TIMEOUT_MS:
                self.state.leader.active = False
                self.state.leader.sequence = ""
                self.state.leader.started_at_ms = None

    def _maybe_timeout_delete(self, now_ms: int) -> None:
        if self._pending_delete["active"]:
            if now_ms - self._pending_delete["started_at"] > DELETE_TIMEOUT_MS:
                self._pending_delete["active"] = False

    def _handle_leader_input(self, ch: int) -> bool | None:
        leader = self.state.leader

        if ch == KEY_ESC:
            leader.active = False
            leader.sequence = ""
            leader.started_at_ms = None
            return True

        if ch < 0 or ch > 255:
            leader.active = False
            leader.sequence = ""
            leader.started_at_ms = None
            return True

        char = chr(ch)
        sequence = leader.sequence + char
        leader.sequence = sequence
        leader.started_at_ms = int(time.time() * 1000)

        if self.state.view != "agenda":
            leader.active = False
            leader.sequence = ""
            leader.started_at_ms = None
            return None

        if sequence == "x":
            return True

        if sequence == "xa":
            return True

        if sequence == "xar":
            self.state.agenda_expand_all = True
            self.state.agenda_row_overrides.clear()
            leader.active = False
            leader.sequence = ""
            leader.started_at_ms = None
            return True

        if sequence == "xc":
            self.state.agenda_expand_all = False
            self.state.agenda_row_overrides.clear()
            leader.active = False
            leader.sequence = ""
            leader.started_at_ms = None
            return True

        if sequence == "xr":
            visible = self._visible_agenda_events()
            if visible:
                idx = max(0, min(self.state.agenda_index, len(visible) - 1))
                identity = self._event_identity(visible[idx])
                overrides = self.state.agenda_row_overrides
                if identity in overrides:
                    overrides.remove(identity)
                else:
                    overrides.add(identity)
            leader.active = False
            leader.sequence = ""
            leader.started_at_ms = None
            return True

        leader.active = False
        leader.sequence = ""
        leader.started_at_ms = None
        return None

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
            visible = self._visible_agenda_events()
            if not visible:
                return False
            idx = max(0, min(self.state.agenda_index, len(visible) - 1))
            target = visible[idx]
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
            self._ensure_agenda_index_bounds(len(self._visible_agenda_events()))
        else:
            month_events = self._month_events_for_selected_date()
            self.state.month_event_index = min(
                self.state.month_event_index, max(len(month_events) - 1, 0)
            )
        self._prune_row_overrides()
        return True

    # Agenda behaviors
    def _handle_agenda_keys(self, ch: int) -> bool:
        visible = self._visible_agenda_events()
        view = AgendaView(visible)
        if ch == KEY_J:
            self.state.agenda_index = view.move_selection(self.state.agenda_index, +1)
            return True
        if ch == KEY_K:
            self.state.agenda_index = view.move_selection(self.state.agenda_index, -1)
            return True
        if ch == KEY_H:
            self.state.agenda_col = view.clamp_column(self.state.agenda_col - 1)
            return True
        if ch == KEY_L:
            self.state.agenda_col = view.clamp_column(self.state.agenda_col + 1)
            return True
        if ch == ord("H"):
            return self._agenda_jump_day(-1)
        if ch == ord("L"):
            return self._agenda_jump_day(+1)
        return False

    def _agenda_jump_day(self, direction: int) -> bool:
        visible = self._visible_agenda_events()
        if not visible:
            return False
        cur_idx = max(0, min(self.state.agenda_index, len(visible) - 1))
        cur_day = visible[cur_idx].coords.x.date()
        if direction < 0:
            for idx in range(cur_idx - 1, -1, -1):
                if visible[idx].coords.x.date() < cur_day:
                    target_day = visible[idx].coords.x.date()
                    first_idx = next(
                        (
                            i
                            for i, ev in enumerate(visible)
                            if ev.coords.x.date() == target_day
                        ),
                        idx,
                    )
                    self.state.agenda_index = first_idx
                    return True
        else:
            for idx in range(cur_idx + 1, len(visible)):
                if visible[idx].coords.x.date() > cur_day:
                    self.state.agenda_index = idx
                    return True
        return False

    # Month behaviors
    def _handle_month_keys(self, ch: int) -> bool:
        filtered_events = self._bucket_filtered_events()
        view = MonthView(filtered_events)
        if self.state.month_focus == "grid":
            if ch in (ord("\n"), curses.KEY_ENTER):
                if self._month_events_for_selected_date():
                    self.state.month_focus = "events"
                    self.state.month_event_index = view.clamp_event_index(
                        self.state.month_selected_date, self.state.month_event_index
                    )
                    self.state.month_event_col = max(
                        0, min(self.state.month_event_col, 2)
                    )
                    return True
                return False
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
            if ch == KEY_CTRL_K:
                self.state.month_selected_date = view.move_month(
                    self.state.month_selected_date, -12
                )
                self.state.month_event_index = 0
                return True
            if ch == KEY_CTRL_J:
                self.state.month_selected_date = view.move_month(
                    self.state.month_selected_date, +12
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
        else:  # focus == events
            if ch in (ord("\n"), curses.KEY_ENTER):
                self.state.month_focus = "grid"
                return True
            if ch == KEY_H:
                self.state.month_event_col = max(0, self.state.month_event_col - 1)
                return True
            if ch == KEY_L:
                self.state.month_event_col = min(2, self.state.month_event_col + 1)
                return True
            if ch in (KEY_CTRL_H, KEY_CTRL_L, KEY_CTRL_J, KEY_CTRL_K):
                self.state.month_focus = "grid"
                self.state.month_event_index = 0
                return self._handle_month_keys(ch)
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
            if ch == KEY_CTRL_K:
                self.state.month_selected_date = view.move_month(
                    self.state.month_selected_date, -12
                )
                self.state.month_event_index = 0
                if not view.events_by_date.get(self.state.month_selected_date):
                    self.state.month_focus = "grid"
                return True
            if ch == KEY_CTRL_J:
                self.state.month_selected_date = view.move_month(
                    self.state.month_selected_date, +12
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
            visible = self._visible_agenda_events()
            if not visible:
                self.state.agenda_index = 0
                self.state.agenda_scroll = 0
                return True
            view = AgendaView(visible)
            self.state.agenda_index = view.jump_to_today()
            self._ensure_agenda_index_bounds(len(visible))
            return True
        else:
            self.state.month_selected_date = today
            self.state.month_event_index = 0
            return True

    # Editing / creating
    def _edit_or_create(
        self, stdscr: "curses.window", *, force_new: bool = False
    ) -> bool:  # type: ignore[name-defined]
        if self.state.view == "agenda":
            visible = self._visible_agenda_events()
            seeds = self._seed_events_for_agenda(force_new=force_new)
            allow_overwrite = not force_new and bool(visible)
            originals_source = (
                [visible[self.state.agenda_index]]
                if allow_overwrite and 0 <= self.state.agenda_index < len(visible)
                else []
            )
            single_event_payload = len(seeds) == 1
        else:
            month_events = self._month_events_for_selected_date()
            has_existing = bool(month_events)
            select_single = (
                not force_new and self.state.month_focus == "events" and has_existing
            )
            seeds = self._seed_events_for_month(
                force_new=force_new, selected_only=select_single
            )
            allow_overwrite = not force_new and has_existing
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
        editor_cmd = os.environ.get("EDITOR", "vim")
        ok, result = edit_event_via_editor(editor_cmd, payload)
        curses.reset_prog_mode()

        stdscr.refresh()
        curses.curs_set(0)
        stdscr.nodelay(True)
        stdscr.timeout(100)

        if not ok:
            # Editor failed or was cancelled; message already surfaced if needed.
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
                if original is not None:
                    self._replace_row_override(original, ev)
            self.state.events = new_events
            self._pending_delete["active"] = False
            # Rebuild any derived selection indices sensibly
            if self.state.view == "agenda":
                if updated_events:
                    self._reselect_agenda_event(updated_events[0])
            else:
                self.state.month_event_index = 0
            self._prune_row_overrides()
        except ValidationError:
            # Ignore invalid payloads; keep existing events unchanged.
            pass
        except StorageError as exc:
            self._show_overlay(stdscr, f"Storage error: {exc}", kind="error")
        return True

    def _edit_agenda_cell(self, stdscr: "curses.window") -> bool:  # type: ignore[name-defined]
        visible = self._visible_agenda_events()
        if not visible:
            return False

        idx = max(0, min(self.state.agenda_index, len(visible) - 1))
        event = visible[idx]
        column = max(0, min(self.state.agenda_col, AgendaView.COLUMN_COUNT - 1))
        self.state.agenda_col = column
        editor_cmd = os.environ.get("EDITOR", "vim")

        if column == 0:
            seed_value = event.coords.x.strftime(DATETIME_FMT)
        elif column == 1:
            seed_value = event.coords.y
        else:
            seed_value = event.coords.z

        curses.def_prog_mode()
        curses.endwin()
        try:
            ok, payload = self._launch_single_value_editor(editor_cmd, seed_value)
        finally:
            curses.reset_prog_mode()
            stdscr.refresh()
            try:
                curses.curs_set(0)
            except curses.error:
                pass
            stdscr.nodelay(True)
            stdscr.timeout(100)

        if not ok:
            # Editor cancelled or failed; nothing to do.
            return True

        if payload is None:
            return True

        updated_event = event
        if column == 0:
            new_value = payload.strip()
            if not new_value:
                return True
            try:
                new_dt = parse_datetime(new_value)
            except ValidationError as exc:
                return True
            if new_dt == event.coords.x:
                return True
            updated_event = event.with_updated(x=new_dt)
        elif column == 1:
            new_value = payload.strip()
            if not new_value:
                return True
            if new_value == event.coords.y:
                return True
            updated_event = event.with_updated(y=new_value)
        else:
            new_value = payload.strip()
            if not new_value:
                return True
            if new_value == event.coords.z:
                return True
            updated_event = event.with_updated(z=new_value)

        try:
            new_events = self.calendar.upsert_event(
                self.state.events,
                updated_event,
                replace_dt=(True, event),
            )
        except ValidationError:
            return True
        except StorageError as exc:
            self._show_overlay(stdscr, str(exc), kind="error")
            return True

        self._replace_row_override(event, updated_event)
        self.state.events = new_events
        self._reselect_agenda_event(updated_event)
        self._prune_row_overrides()
        return True

    def _edit_agenda_bucket(self, stdscr: "curses.window") -> bool:  # type: ignore[name-defined]
        visible = self._visible_agenda_events()
        if not visible:
            return False

        idx = max(0, min(self.state.agenda_index, len(visible) - 1))
        event = visible[idx]

        curses.def_prog_mode()
        curses.endwin()
        try:
            ok, payload = self._launch_single_value_editor(
                os.environ.get("EDITOR", "vim"), event.bucket
            )
        finally:
            curses.reset_prog_mode()
            stdscr.refresh()
            try:
                curses.curs_set(0)
            except curses.error:
                pass
            stdscr.nodelay(True)
            stdscr.timeout(100)

        if not ok:
            # Editor cancelled or failed; nothing to report.
            return True

        if payload is None:
            return True

        new_bucket = payload.strip().lower()
        if not new_bucket:
            return True
        if new_bucket not in BUCKETS:
            valid = ", ".join(BUCKETS)
            self._show_overlay(
                stdscr,
                f"Invalid bucket '{new_bucket}'. Expected one of: {valid}",
                kind="error",
            )
            return True

        bucket_name = cast(BucketName, new_bucket)
        if bucket_name == event.bucket:
            return True

        updated_event = event.with_updated(bucket=bucket_name)

        try:
            new_events = self.calendar.upsert_event(
                self.state.events,
                updated_event,
                replace_dt=(True, event),
            )
        except (ValidationError, StorageError) as exc:
            self._show_overlay(stdscr, str(exc), kind="error")
            return True

        self._replace_row_override(event, updated_event)
        self.state.events = new_events
        self._reselect_agenda_event(updated_event)
        self._prune_row_overrides()
        return True

    def _edit_month_cell(self, stdscr: "curses.window") -> bool:  # type: ignore[name-defined]
        events = self._month_events_for_selected_date()
        if not events:
            return False

        idx = max(0, min(self.state.month_event_index, len(events) - 1))
        event = events[idx]
        column = max(0, min(self.state.month_event_col, 2))
        self.state.month_event_col = column
        editor_cmd = os.environ.get("EDITOR", "vim")

        if column == 0:
            seed_value = event.coords.x.strftime(DATETIME_FMT)
        elif column == 1:
            seed_value = event.coords.y
        else:
            seed_value = event.coords.z

        curses.def_prog_mode()
        curses.endwin()
        try:
            ok, payload = self._launch_single_value_editor(editor_cmd, seed_value)
        finally:
            curses.reset_prog_mode()
            stdscr.refresh()
            try:
                curses.curs_set(0)
            except curses.error:
                pass
            stdscr.nodelay(True)
            stdscr.timeout(100)

        if not ok or payload is None:
            return True

        updated_event = event
        if column == 0:
            new_value = payload.strip()
            if not new_value:
                return True
            try:
                new_dt = parse_datetime(new_value)
            except ValidationError:
                return True
            if new_dt == event.coords.x:
                return True
            updated_event = event.with_updated(x=new_dt)
        elif column == 1:
            new_value = payload.strip()
            if not new_value or new_value == event.coords.y:
                return True
            updated_event = event.with_updated(y=new_value)
        else:
            new_value = payload.strip()
            if not new_value or new_value == event.coords.z:
                return True
            updated_event = event.with_updated(z=new_value)

        try:
            new_events = self.calendar.upsert_event(
                self.state.events,
                updated_event,
                replace_dt=(True, event),
            )
        except ValidationError:
            return True
        except StorageError as exc:
            self._show_overlay(stdscr, str(exc), kind="error")
            return True

        self._replace_row_override(event, updated_event)
        self.state.events = new_events
        self._reselect_month_event(updated_event)
        self._prune_row_overrides()
        return True

    def _edit_month_bucket(self, stdscr: "curses.window") -> bool:  # type: ignore[name-defined]
        events = self._month_events_for_selected_date()
        if not events:
            return False

        idx = max(0, min(self.state.month_event_index, len(events) - 1))
        event = events[idx]

        curses.def_prog_mode()
        curses.endwin()
        try:
            ok, payload = self._launch_single_value_editor(
                os.environ.get("EDITOR", "vim"), event.bucket
            )
        finally:
            curses.reset_prog_mode()
            stdscr.refresh()
            try:
                curses.curs_set(0)
            except curses.error:
                pass
            stdscr.nodelay(True)
            stdscr.timeout(100)

        if not ok or payload is None:
            return True

        new_bucket = payload.strip().lower()
        if not new_bucket:
            return True
        if new_bucket not in BUCKETS:
            valid = ", ".join(BUCKETS)
            self._show_overlay(
                stdscr,
                f"Invalid bucket '{new_bucket}'. Expected one of: {valid}",
                kind="error",
            )
            return True

        bucket_name = cast(BucketName, new_bucket)
        if bucket_name == event.bucket:
            return True

        updated_event = event.with_updated(bucket=bucket_name)

        try:
            new_events = self.calendar.upsert_event(
                self.state.events,
                updated_event,
                replace_dt=(True, event),
            )
        except ValidationError:
            return True
        except StorageError as exc:
            self._show_overlay(stdscr, str(exc), kind="error")
            return True

        self._replace_row_override(event, updated_event)
        self.state.events = new_events
        self._reselect_month_event(updated_event)
        self._prune_row_overrides()
        return True

    def _launch_single_value_editor(
        self, editor_cmd: str, seed_value: str
    ) -> tuple[bool, str | None]:
        cmd = shlex.split(editor_cmd) if editor_cmd and editor_cmd.strip() else ["vim"]
        with tempfile.NamedTemporaryFile(
            "w+", suffix=".txt", delete=False, encoding="utf-8"
        ) as tmp:
            tmp_path = Path(tmp.name)
            tmp.write(seed_value)
            tmp.flush()
        try:
            try:
                proc = subprocess.run(cmd + [str(tmp_path)], check=False)
            except FileNotFoundError:
                return False, f"Editor not found: {cmd[0]}"
            except Exception as exc:  # noqa: BLE001
                return False, f"Editor failed: {exc}"

            if proc.returncode != 0:
                return False, None

            try:
                contents = tmp_path.read_text(encoding="utf-8")
            except Exception as exc:  # noqa: BLE001
                return False, f"Failed to read edited value: {exc}"

            return True, contents.rstrip("\n")
        finally:
            try:
                tmp_path.unlink()
            except Exception:
                pass

    def _visible_agenda_events(self) -> List[Event]:
        return self._bucket_filtered_events()

    def _bucket_filtered_events(self) -> List[Event]:
        if self.state.agenda_bucket_filter == ALL_BUCKET:
            return list(self.state.events)
        return [
            ev
            for ev in self.state.events
            if ev.bucket == self.state.agenda_bucket_filter
        ]

    def _ensure_agenda_index_bounds(self, visible_length: int) -> None:
        if visible_length <= 0:
            self.state.agenda_index = 0
            self.state.agenda_scroll = 0
        else:
            self.state.agenda_index = max(
                0, min(self.state.agenda_index, visible_length - 1)
            )
            self.state.agenda_scroll = max(
                0, min(self.state.agenda_scroll, visible_length - 1)
            )
        self.state.agenda_col = max(
            0, min(self.state.agenda_col, AgendaView.COLUMN_COUNT - 1)
        )

    def _cycle_agenda_bucket(self) -> None:
        options: List[str] = [ALL_BUCKET, *BUCKETS]
        try:
            current_idx = options.index(self.state.agenda_bucket_filter)
        except ValueError:
            current_idx = 0
        new_filter = options[(current_idx + 1) % len(options)]
        self.state.agenda_bucket_filter = new_filter
        self.state.agenda_index = 0
        self.state.agenda_scroll = 0
        self.state.month_event_index = 0
        self.state.month_event_col = 0
        self._ensure_agenda_index_bounds(len(self._visible_agenda_events()))

    @staticmethod
    def _event_identity(event: Event) -> tuple:
        return (
            event.bucket,
            event.coords.x,
            event.coords.y,
            event.coords.z,
        )

    def _reselect_agenda_event(self, target: Event) -> None:
        visible = self._visible_agenda_events()
        target_identity = self._event_identity(target)
        for idx, ev in enumerate(visible):
            if self._event_identity(ev) == target_identity:
                self.state.agenda_index = idx
                break
        else:
            self.state.agenda_index = 0 if visible else 0
        self._ensure_agenda_index_bounds(len(visible))

    def _reselect_month_event(self, target: Event) -> None:
        target_day = target.coords.x.date()
        if target_day != self.state.month_selected_date:
            self.state.month_selected_date = target_day
        events = self._month_events_for_selected_date()
        identity = self._event_identity(target)
        for idx, ev in enumerate(events):
            if self._event_identity(ev) == identity:
                self.state.month_event_index = idx
                break
        else:
            self.state.month_event_index = min(
                self.state.month_event_index, max(len(events) - 1, 0)
            )
        self.state.month_event_col = max(0, min(self.state.month_event_col, 2))

    def _prune_row_overrides(self) -> None:
        valid = {self._event_identity(ev) for ev in self.state.events}
        self.state.agenda_row_overrides.intersection_update(valid)

    def _replace_row_override(self, old_event: Event | None, new_event: Event) -> None:
        if old_event is None:
            return
        old_identity = self._event_identity(old_event)
        overrides = self.state.agenda_row_overrides
        if old_identity in overrides:
            overrides.remove(old_identity)
            overrides.add(self._event_identity(new_event))

    def _seed_events_for_agenda(self, *, force_new: bool = False) -> List[Event]:
        visible = self._visible_agenda_events()
        if not force_new and visible and 0 <= self.state.agenda_index < len(visible):
            return [visible[self.state.agenda_index]]
        today = date.today()
        dt_str = f"{today.strftime('%Y-%m-%d')} {SEEDED_DEFAULT_TIME}"
        bucket_filter = self.state.agenda_bucket_filter
        bucket = (
            DEFAULT_BUCKET
            if bucket_filter == ALL_BUCKET
            else cast(BucketName, bucket_filter)
        )
        return [
            Event(
                bucket=bucket,
                coords=Coordinates(
                    x=parse_datetime(dt_str),
                    y="",
                    z="",
                ),
            )
        ]

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
        return [
            Event(
                bucket=DEFAULT_BUCKET,
                coords=Coordinates(
                    x=parse_datetime(dt_str),
                    y="",
                    z="",
                ),
            )
        ]

    def _month_events_for_selected_date(self) -> List[Event]:
        sel_day = self.state.month_selected_date
        return [
            e for e in self._bucket_filtered_events() if e.coords.x.date() == sel_day
        ]

    def _show_overlay(
        self, stdscr: "curses.window", message: str, kind: str = "error"
    ) -> None:  # type: ignore[name-defined]
        self.state.overlay = "error" if kind == "error" else "message"
        self.state.overlay_message = message
        self._draw(stdscr)


__all__ = ["Orchestrator"]
