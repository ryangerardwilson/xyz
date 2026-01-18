#!/usr/bin/env python3
"""Intent definitions and schemas for tcal natural-language commands."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional, Union

from models import Event, normalize_event_payload, parse_datetime

CREATE_EVENT_INTENT = "create_event"
LIST_EVENTS_INTENT = "list_events"
RESCHEDULE_EVENT_INTENT = "reschedule_event"

VALID_RANGE_VALUES = [
    "day_before_yesterday",
    "yesterday",
    "today",
    "tomorrow",
    "this_week",
    "this_month",
    "next_month",
    "last_month",
    "this_year",
    "all",
]

INTENT_JSON_SCHEMA = {
    "name": "calendar_intent",
    "schema": {
        "type": "object",
        "properties": {
            "intent": {
                "type": "string",
                "enum": [
                    CREATE_EVENT_INTENT,
                    LIST_EVENTS_INTENT,
                    RESCHEDULE_EVENT_INTENT,
                ],
            },
            "data": {
                "type": "object",
                "properties": {
                    "datetime": {"type": "string"},
                    "event": {"type": "string"},
                    "details": {"type": "string"},
                    "range": {"type": "string", "enum": VALID_RANGE_VALUES},
                    "keyword": {"type": "string"},
                    "target_description": {"type": "string"},
                    "new_datetime": {"type": "string"},
                    "relative_amount": {"type": "integer"},
                    "relative_unit": {
                        "type": "string",
                        "enum": ["minutes", "hours", "days", "weeks"],
                    },
                },
                "additionalProperties": False,
            },
        },
        "required": ["intent", "data"],
        "additionalProperties": False,
    },
}

INTENT_RESPONSE_FORMAT = {
    "type": "json_schema",
    "json_schema": INTENT_JSON_SCHEMA,
}


@dataclass
class CreateEventIntent:
    event: Event


@dataclass
class ListEventsIntent:
    range: str
    keyword: str | None = None


@dataclass
class RelativeAdjustment:
    amount: int
    unit: str


@dataclass
class RescheduleEventIntent:
    target_description: str
    new_datetime: datetime | None = None
    relative_adjustment: RelativeAdjustment | None = None


Intent = Union[CreateEventIntent, ListEventsIntent, RescheduleEventIntent]


class IntentParseError(Exception):
    """Raised when an OpenAI response cannot be parsed into an intent."""


def parse_intent_payload(payload: Dict[str, Any]) -> Intent:
    """Convert a JSON payload into a strongly-typed intent."""
    if not isinstance(payload, dict):
        raise IntentParseError("Intent payload must be an object")

    intent_name = payload.get("intent")
    data = payload.get("data")

    if not isinstance(data, dict):
        raise IntentParseError("Intent data must be an object")

    if intent_name == CREATE_EVENT_INTENT:
        event = normalize_event_payload(data)
        return CreateEventIntent(event=event)

    if intent_name == LIST_EVENTS_INTENT:
        range_value = data.get("range")
        if range_value not in VALID_RANGE_VALUES:
            raise IntentParseError(f"Invalid range value: {range_value}")
        keyword = data.get("keyword")
        if keyword is not None and not isinstance(keyword, str):
            raise IntentParseError("keyword must be a string if provided")
        return ListEventsIntent(range=range_value, keyword=(keyword or None))

    if intent_name == RESCHEDULE_EVENT_INTENT:
        target_description = data.get("target_description")
        if not isinstance(target_description, str) or not target_description.strip():
            raise IntentParseError("target_description must be a non-empty string")

        new_datetime_value = data.get("new_datetime")
        relative_amount = data.get("relative_amount")
        relative_unit = data.get("relative_unit")

        new_dt: datetime | None = None
        if new_datetime_value is not None:
            new_dt = parse_datetime(str(new_datetime_value))

        relative_adjustment: RelativeAdjustment | None = None
        if relative_amount is not None or relative_unit is not None:
            if not isinstance(relative_amount, int) or relative_unit not in {"minutes", "hours", "days", "weeks"}:
                raise IntentParseError(
                    "relative_amount must be int and relative_unit one of minutes/hours/days/weeks"
                )
            relative_adjustment = RelativeAdjustment(amount=relative_amount, unit=relative_unit)

        if not new_dt and not relative_adjustment:
            raise IntentParseError("reschedule intent requires new_datetime or relative adjustment")

        if new_dt and relative_adjustment:
            # Prefer absolute datetime if both provided
            relative_adjustment = None

        return RescheduleEventIntent(
            target_description=target_description.strip(),
            new_datetime=new_dt,
            relative_adjustment=relative_adjustment,
        )

    raise IntentParseError(f"Unsupported intent: {intent_name}")


__all__ = [
    "CreateEventIntent",
    "ListEventsIntent",
    "RelativeAdjustment",
    "RescheduleEventIntent",
    "Intent",
    "IntentParseError",
    "INTENT_RESPONSE_FORMAT",
    "parse_intent_payload",
    "CREATE_EVENT_INTENT",
    "LIST_EVENTS_INTENT",
    "RESCHEDULE_EVENT_INTENT",
    "VALID_RANGE_VALUES",
]
