#!/usr/bin/env python3
"""Core models and validation helpers for tcal."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

DATETIME_FMT = "%Y-%m-%d %H:%M:%S"


@dataclass
class Event:
    datetime: datetime
    event: str
    details: str = ""

    def with_updated(
        self,
        *,
        dt: Optional[datetime] = None,
        event: Optional[str] = None,
        details: Optional[str] = None,
    ) -> "Event":
        return Event(
            datetime=dt if dt is not None else self.datetime,
            event=event if event is not None else self.event,
            details=details if details is not None else self.details,
        )


class ValidationError(Exception):
    pass


def parse_datetime(value: str) -> datetime:
    value = value.strip()

    # Accept ISO-8601 formats like YYYY-MM-DDTHH:MM[:SS][Z]
    iso_candidate = value
    if iso_candidate.endswith("Z"):
        iso_candidate = iso_candidate[:-1]
    iso_candidate = iso_candidate.replace("T", " ")
    try:
        return datetime.fromisoformat(iso_candidate)
    except ValueError:
        pass

    # Accept YYYY-MM-DD HH:MM and normalize seconds
    try:
        if len(value) == 16 and "T" not in value:  # YYYY-MM-DD HH:MM
            value = f"{value}:00"
        return datetime.strptime(value, DATETIME_FMT)
    except ValueError as exc:
        raise ValidationError(
            f"Invalid datetime format: '{value}'. Expected YYYY-MM-DD HH:MM[:SS]"
        ) from exc


def normalize_event_payload(data: dict) -> Event:
    if "datetime" not in data or "event" not in data:
        raise ValidationError("Missing 'datetime' or 'event' field")

    dt = parse_datetime(str(data["datetime"]))
    ev = str(data["event"]).strip()
    if not ev:
        raise ValidationError("'event' cannot be empty")

    details = str(data.get("details", ""))
    return Event(datetime=dt, event=ev, details=details)


def event_to_jsonable(event: Event) -> dict:
    return {
        "datetime": event.datetime.strftime(DATETIME_FMT),
        "event": event.event,
        "details": event.details,
    }


__all__ = [
    "Event",
    "ValidationError",
    "parse_datetime",
    "normalize_event_payload",
    "event_to_jsonable",
    "DATETIME_FMT",
]
