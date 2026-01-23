#!/usr/bin/env python3
"""App state container for xyz."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Literal, Optional, List

from models import Event, ALL_BUCKET

ViewName = Literal["agenda", "month"]

FocusName = Literal["grid", "events"]
OverlayKind = Literal["none", "help", "error", "message"]


@dataclass
class LeaderState:
    active: bool = False
    started_at_ms: Optional[int] = None
    sequence: str = ""


@dataclass
class AppState:
    view: ViewName = "month"
    leader: LeaderState = field(default_factory=LeaderState)
    overlay: OverlayKind = "none"
    overlay_message: str = ""
    focused_date: date = field(default_factory=lambda: date.today())

    events: List[Event] = field(default_factory=list)

    # Agenda selection
    agenda_index: int = 0
    agenda_scroll: int = 0
    agenda_expand_all: bool = True
    agenda_col: int = 0
    agenda_bucket_filter: str = ALL_BUCKET

    # Month view
    month_focus: FocusName = "grid"
    month_selected_date: date = field(default_factory=lambda: date.today())
    month_event_index: int = 0


__all__ = ["AppState", "LeaderState", "ViewName", "FocusName", "OverlayKind"]
