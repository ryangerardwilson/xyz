#!/usr/bin/env python3
"""Action handlers for calendar intents."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Iterable, List

from calendar_service import CalendarService
from date_ranges import resolve_date_range
from intents import (
    CreateEventIntent,
    ListEventsIntent,
    RescheduleEventIntent,
    RelativeAdjustment,
)
from models import Event, ValidationError, normalize_event_payload, parse_datetime
from store import StorageError


@dataclass
class ActionResult:
    success: bool
    message: str
    events: List[Event] | None = None


class ActionError(Exception):
    pass


def _missing_components(event: Event) -> list[str]:
    missing: list[str] = []
    if not event.x:
        missing.append("x (trigger)")
    if not event.y.strip():
        missing.append("y (outcome)")
    if not event.z.strip():
        missing.append("z (impact)")
    return missing


def _infer_impact_clause(outcome: str) -> str:
    lower = outcome.lower()
    if any(word in lower for word in ["cook", "cooking", "meal", "kitchen"]):
        return "serve affordable, nutritious meals for myself and friends"
    if any(word in lower for word in ["study", "learn", "learning", "exam", "course", "class"]):
        return "confidently tackle advanced coursework and related opportunities"
    if any(word in lower for word in ["exercise", "fitness", "run", "workout", "train"]):
        return "build long-term health, energy, and resilience"
    return "unlock new opportunities and turn this effort into tangible momentum"


def _format_missing_component_message(
    event: Event,
    missing: list[str],
    *,
    raw_x: str | None = None,
) -> str:
    def _normalize_missing(entries: list[str]) -> list[str]:
        mapping = {
            "x (trigger)": "x",
            "y (outcome)": "y",
            "z (impact)": "z",
        }
        normalized = []
        for item in entries:
            normalized.append(mapping.get(item, item))
        return normalized

    def _format_x_value() -> str:
        if "x (trigger)" in missing:
            return raw_x or ""
        return event.x.strftime("%Y-%m-%d %H:%M:%S")

    def _format_y_value() -> str:
        if "y (outcome)" in missing:
            return ""
        return event.y.strip()

    def _format_z_value() -> str:
        if "z (impact)" in missing:
            return ""
        return event.z.strip()

    parsed: dict[str, str] = {}
    if "x (trigger)" not in missing:
        parsed["x"] = _format_x_value()
    if "y (outcome)" not in missing:
        parsed["y"] = _format_y_value()
    if "z (impact)" not in missing:
        parsed["z"] = _format_z_value()

    payload = {
        "missing": _normalize_missing(missing),
        "parsed": parsed,
    }
    return json.dumps(payload, indent=2)


def handle_create_event(
    intent: CreateEventIntent,
    calendar: CalendarService,
    *,
    existing_events: List[Event],
) -> ActionResult:
    raw_data = intent.data
    created: Event | None = None
    create_error: str | None = None
    try:
        created = normalize_event_payload(raw_data)
    except ValidationError as exc:
        create_error = str(exc)

    if created is None:
        # Determine which components are missing/invalid for better feedback
        missing = []
        raw_x = raw_data.get("x") or raw_data.get("datetime")
        raw_y = raw_data.get("y") or raw_data.get("event")
        raw_z = raw_data.get("z") or raw_data.get("details")
        if not raw_x:
            missing.append("x (trigger)")
        if not str(raw_y or "").strip():
            missing.append("y (outcome)")
        if not str(raw_z or "").strip():
            missing.append("z (impact)")
        if not missing and create_error:
            return ActionResult(False, create_error)
        placeholder_event = Event(
            x=parse_datetime(raw_x or date.today().strftime("%Y-%m-%d 00:00:00")),
            y=str(raw_y or "(unspecified outcome)"),
            z=str(raw_z or ""),
        )
        return ActionResult(
            False,
            _format_missing_component_message(
                placeholder_event,
                missing or ["x (trigger)"],
                raw_x=raw_x,
            ),
        )

    missing = _missing_components(created)
    if missing:
        return ActionResult(success=False, message=_format_missing_component_message(created, missing))

    try:
        updated = calendar.upsert_event(existing_events, created)
    except ValidationError as exc:
        return ActionResult(success=False, message=f"Validation error: {exc}")
    except StorageError as exc:
        return ActionResult(success=False, message=f"Storage error: {exc}")

    payload = {
        "x": created.x.strftime("%Y-%m-%d %H:%M:%S"),
        "y": created.y,
        "z": created.z,
    }
    pretty = json.dumps(payload, indent=2)
    return ActionResult(
        success=True,
        message=pretty,
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
