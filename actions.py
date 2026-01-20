#!/usr/bin/env python3
"""Action handlers for calendar intents."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Iterable, List

from calendar_service import CalendarService
from date_ranges import resolve_date_range
from intents import (
    CreateEventIntent,
    ListEventsIntent,
    RescheduleEventIntent,
    RelativeAdjustment,
)
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

    created = intent.event
    impact_suffix = f" with impact '{created.z}'" if created.z else ""
    return ActionResult(
        success=True,
        message=f"Created task '{created.y}' at {created.x}{impact_suffix}",
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


def handle_reschedule_event(
    intent: RescheduleEventIntent,
    calendar: CalendarService,
    *,
    existing_events: List[Event],
) -> ActionResult:
    matches = _match_events(existing_events, intent.target_description)
    if not matches:
        return ActionResult(False, f"No tasks found matching '{intent.target_description}'.")
    if len(matches) > 1:
        options = ", ".join(f"{ev.y} ({ev.x:%Y-%m-%d %H:%M})" for ev in matches[:5])
        if len(matches) > 5:
            options += ", …"
        return ActionResult(False, f"Multiple tasks match '{intent.target_description}': {options}")

    original = matches[0]

    if intent.new_datetime:
        new_dt = intent.new_datetime
    elif intent.relative_adjustment:
        new_dt = _apply_relative_adjustment(original.x, intent.relative_adjustment)
    else:
        return ActionResult(False, "No new trigger (x) provided for reschedule.")

    updated_event = original.with_updated(x=new_dt)

    try:
        updated_events = calendar.upsert_event(
            existing_events,
            updated_event,
            replace_dt=(True, original),
        )
    except (ValidationError, StorageError) as exc:
        return ActionResult(False, str(exc))

    verb = "Rescheduled"
    if intent.relative_adjustment and not intent.new_datetime:
        verb = "Adjusted"
    message = (
        f"{verb} '{original.y}' from {original.x:%Y-%m-%d %H:%M}"
        f" to {new_dt:%Y-%m-%d %H:%M}."
    )
    return ActionResult(True, message, events=updated_events)


def _match_events(events: Iterable[Event], description: str) -> List[Event]:
    needle = description.lower()
    matches = [
        ev
        for ev in events
        if needle in ev.y.lower() or needle in ev.z.lower()
    ]
    return matches


def _apply_relative_adjustment(
    original: datetime,
    adjustment: RelativeAdjustment,
) -> datetime:
    units = {
        "minutes": timedelta(minutes=adjustment.amount),
        "hours": timedelta(hours=adjustment.amount),
        "days": timedelta(days=adjustment.amount),
        "weeks": timedelta(weeks=adjustment.amount),
    }
    if adjustment.unit not in units:
        raise ValidationError(f"Unsupported relative unit: {adjustment.unit}")
    return original + units[adjustment.unit]


def _format_event_list(
    events: Iterable[Event], range_name: str, keyword: str | None
) -> str:
    events = list(events)
    if not events:
        if keyword:
            return f"No tasks found for {range_name.replace('_', ' ')} matching '{keyword}'."
        return f"No tasks found for {range_name.replace('_', ' ')}."

    header = f"{range_name.replace('_', ' ').title()} tasks"
    if keyword:
        header += f" matching '{keyword}'"
    header += f" ({len(events)})"

    lines = [header]
    for ev in events[:10]:
        impact = f" — {ev.z}" if ev.z else ""
        lines.append(
            f"- {ev.x.strftime('%Y-%m-%d %H:%M')} {ev.y}{impact}"
        )
    if len(events) > 10:
        lines.append(f"…and {len(events) - 10} more tasks")
    return "\n".join(lines)


__all__ = [
    "ActionResult",
    "ActionError",
    "handle_create_event",
    "handle_list_events",
    "handle_reschedule_event",
]
