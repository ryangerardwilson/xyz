#!/usr/bin/env python3
"""Intent definitions and schemas for tcal natural-language commands."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, Union

from models import Event, normalize_event_payload

CREATE_EVENT_INTENT = "create_event"
LIST_EVENTS_INTENT = "list_events"

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
                "enum": [CREATE_EVENT_INTENT, LIST_EVENTS_INTENT],
            },
            "data": {
                "type": "object",
                "properties": {
                    "datetime": {"type": "string"},
                    "event": {"type": "string"},
                    "details": {"type": "string"},
                    "range": {"type": "string", "enum": VALID_RANGE_VALUES},
                    "keyword": {"type": "string"},
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


Intent = Union[CreateEventIntent, ListEventsIntent]


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

    raise IntentParseError(f"Unsupported intent: {intent_name}")


__all__ = [
    "CreateEventIntent",
    "ListEventsIntent",
    "Intent",
    "IntentParseError",
    "INTENT_RESPONSE_FORMAT",
    "parse_intent_payload",
    "CREATE_EVENT_INTENT",
    "LIST_EVENTS_INTENT",
    "VALID_RANGE_VALUES",
]
