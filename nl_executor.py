#!/usr/bin/env python3
"""Natural language executor that routes intents to calendar actions."""

from __future__ import annotations

import json
from typing import List

from actions import ActionResult, handle_create_event
from calendar_service import CalendarService
from intents import INTENT_RESPONSE_FORMAT, IntentParseError, parse_intent_payload
from openai_client import OpenAIAPIError, OpenAIClient
from models import Event

NL_SYSTEM_PROMPT = """
You are an assistant that turns short natural-language calendar commands into structured intents.
Choose the appropriate intent and fill in the required data.
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
        from intents import CreateEventIntent

        if isinstance(intent, CreateEventIntent):
            return handle_create_event(intent, self._calendar, existing_events=existing_events)
        return ActionResult(False, "Unsupported intent type")


__all__ = ["NaturalLanguageExecutor"]
