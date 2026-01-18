#!/usr/bin/env python3
"""Action handlers for calendar intents."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List

from calendar_service import CalendarService
from date_ranges import resolve_date_range
from intents import CreateEventIntent, ListEventsIntent
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


def handle_list_events(
    intent: ListEventsIntent,
    calendar: CalendarService,
    *,
    existing_events: List[Event],
) -> ActionResult:
    try:
        range_info = resolve_date_range(intent.range)
    except ValueError as exc:
        return ActionResult(False, str(exc))

    events = calendar.filter_events_by_range(
        existing_events,
        start=range_info.start,
        end=range_info.end,
    )

    if intent.keyword:
        events = calendar.filter_events_by_keyword(events, intent.keyword)

    message = _format_event_list(events, intent.range, intent.keyword)
    return ActionResult(True, message, events=events)


def _format_event_list(
    events: Iterable[Event], range_name: str, keyword: str | None
) -> str:
    events = list(events)
    if not events:
        if keyword:
            return f"No events found for {range_name.replace('_', ' ')} matching '{keyword}'."
        return f"No events found for {range_name.replace('_', ' ')}."

    header = f"{range_name.replace('_', ' ').title()} events"
    if keyword:
        header += f" matching '{keyword}'"
    header += f" ({len(events)})"

    lines = [header]
    for ev in events[:10]:
        lines.append(
            f"- {ev.datetime.strftime('%Y-%m-%d %H:%M')} {ev.event}" +
            (f" — {ev.details}" if ev.details else "")
        )
    if len(events) > 10:
        lines.append(f"…and {len(events) - 10} more events")
    return "\n".join(lines)


__all__ = [
    "ActionResult",
    "ActionError",
    "handle_create_event",
    "handle_list_events",
]
