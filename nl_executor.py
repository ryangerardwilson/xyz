#!/usr/bin/env python3
"""Natural language executor that routes intents to calendar actions."""

from __future__ import annotations

import json
from typing import List

from actions import ActionResult, handle_create_event, handle_list_events, handle_reschedule_event
from calendar_service import CalendarService
from intents import (
    INTENT_RESPONSE_FORMAT,
    IntentParseError,
    parse_intent_payload,
    CreateEventIntent,
    ListEventsIntent,
    RescheduleEventIntent,
)

from openai_client import OpenAIAPIError, OpenAIClient
from models import Event

NL_SYSTEM_PROMPT = """
You are a task-tracking assistant for a CLI.
Each task has three fields:
- x: timestamp trigger (e.g., "2026-03-01 09:00")
- y: outcome description (what must happen)
- z: impact statement (optional text describing the why/impact)

Supported intents (names remain create_event/list_events/reschedule_event for compatibility):
- create_event: provide x/y/z (z may be empty). Infer x/y/z from the user’s request. Output x in YYYY-MM-DD HH:MM:SS (24h) format.
- list_events: data.range ∈ {day_before_yesterday, yesterday, today, tomorrow, this_week, this_month, next_month, last_month, this_year, all}, optional data.keyword (searches y and z).
- reschedule_event: data.target_description describes which task to move; either data.new_x (ISO/datetime) OR data.relative_amount + data.relative_unit (minutes/hours/days/weeks) to shift the existing x. Positive amount = later, negative = earlier.

Return JSON that matches the provided schema.
""".strip()


class NaturalLanguageExecutor:
    def __init__(self, client: OpenAIClient, calendar: CalendarService) -> None:
        self._client = client
        self._calendar = calendar

    def execute(self, text: str, *, existing_events: List[Event]) -> ActionResult:
        messages = [
            {"role": "system", "content": NL_SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ]

        try:
            response = self._client.run_structured_prompt(
                messages,
                response_format=INTENT_RESPONSE_FORMAT,
                temperature=0,
                max_completion_tokens=256,
            )
        except OpenAIAPIError as exc:
            return ActionResult(False, f"OpenAI error: {exc}")
        except RuntimeError as exc:
            return ActionResult(False, str(exc))

        try:
            payload = json.loads(response.content)
        except json.JSONDecodeError as exc:
            return ActionResult(False, f"Invalid JSON from OpenAI: {exc}")

        try:
            intent = parse_intent_payload(payload)
        except IntentParseError as exc:
            return ActionResult(False, f"Failed to parse intent: {exc}")

        return self._dispatch_intent(intent, existing_events=existing_events)

    def _dispatch_intent(
        self,
        intent,
        *,
        existing_events: List[Event],
    ) -> ActionResult:
        if isinstance(intent, CreateEventIntent):
            return handle_create_event(intent, self._calendar, existing_events=existing_events)
        if isinstance(intent, ListEventsIntent):
            return handle_list_events(intent, self._calendar, existing_events=existing_events)
        if isinstance(intent, RescheduleEventIntent):
            return handle_reschedule_event(intent, self._calendar, existing_events=existing_events)
        return ActionResult(False, "Unsupported intent type")


__all__ = ["NaturalLanguageExecutor"]
