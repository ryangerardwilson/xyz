#!/usr/bin/env python3
"""Action handlers for calendar intents."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from calendar_service import CalendarService
from intents import CreateEventIntent
from models import Event, ValidationError
from store import StorageError


@dataclass
class ActionResult:
    success: bool
    message: str
    events: List[Event] | None = None


class ActionError(Exception):
    pass


def handle_create_event(
    intent: CreateEventIntent,
    calendar: CalendarService,
    *,
    existing_events: List[Event],
) -> ActionResult:
    try:
        updated = calendar.upsert_event(existing_events, intent.event)
    except ValidationError as exc:
        return ActionResult(success=False, message=f"Validation error: {exc}")
    except StorageError as exc:
        return ActionResult(success=False, message=f"Storage error: {exc}")

    return ActionResult(
        success=True,
        message=f"Created event '{intent.event.event}' at {intent.event.datetime}",
        events=updated,
    )


__all__ = ["ActionResult", "ActionError", "handle_create_event"]
