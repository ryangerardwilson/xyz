#!/usr/bin/env python3
"""Intent definitions and schemas for tcal natural-language commands."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, Union

from models import Event, normalize_event_payload

CREATE_EVENT_INTENT = "create_event"

INTENT_JSON_SCHEMA = {
    "name": "calendar_intent",
    "schema": {
        "type": "object",
        "properties": {
            "intent": {
                "type": "string",
                "enum": [CREATE_EVENT_INTENT],
            },
            "data": {
                "type": "object",
                "properties": {
                    "datetime": {"type": "string"},
                    "event": {"type": "string"},
                    "details": {"type": "string"},
                },
                "required": ["datetime", "event"],
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


Intent = Union[CreateEventIntent]


class IntentParseError(Exception):
    """Raised when an OpenAI response cannot be parsed into an intent."""


def parse_intent_payload(payload: Dict[str, Any]) -> Intent:
    """Convert a JSON payload into a strongly-typed intent."""
    if not isinstance(payload, dict):
        raise IntentParseError("Intent payload must be an object")

    intent_name = payload.get("intent")
    data = payload.get("data")

    if intent_name != CREATE_EVENT_INTENT:
        raise IntentParseError(f"Unsupported intent: {intent_name}")
    if not isinstance(data, dict):
        raise IntentParseError("Intent data must be an object")

    event = normalize_event_payload(data)
    return CreateEventIntent(event=event)


__all__ = [
    "CreateEventIntent",
    "Intent",
    "IntentParseError",
    "INTENT_RESPONSE_FORMAT",
    "parse_intent_payload",
    "CREATE_EVENT_INTENT",
]
