#!/usr/bin/env python3
"""Core models and validation helpers for tcal."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

DATETIME_FMT = "%Y-%m-%d %H:%M:%S"


@dataclass
class Event:
    x: datetime  # Timestamp trigger
    y: str       # Outcome description
    z: str = ""  # Impact (optional for now)

    def with_updated(
        self,
        *,
        x: Optional[datetime] = None,
        y: Optional[str] = None,
        z: Optional[str] = None,
    ) -> "Event":
        return Event(
            x=x if x is not None else self.x,
            y=y if y is not None else self.y,
            z=z if z is not None else self.z,
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
    # Accept legacy keys but prefer x/y/z going forward
    x_value = data.get("x", data.get("datetime"))
    y_value = data.get("y", data.get("event"))
    z_value = data.get("z", data.get("details", ""))

    if x_value is None or y_value is None:
        raise ValidationError("Missing 'x' (datetime) or 'y' (outcome) field")

    dt = parse_datetime(str(x_value))
    outcome = str(y_value).strip()
    if not outcome:
        raise ValidationError("'y' (outcome) cannot be empty")

    impact = str(z_value)
    return Event(x=dt, y=outcome, z=impact)


def event_to_jsonable(event: Event) -> dict:
    return {
        "x": event.x.strftime(DATETIME_FMT),
        "y": event.y,
        "z": event.z,
    }


__all__ = [
    "Event",
    "ValidationError",
    "parse_datetime",
    "normalize_event_payload",
    "event_to_jsonable",
    "DATETIME_FMT",
]
