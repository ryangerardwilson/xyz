#!/usr/bin/env python3
"""OpenAI HTTP client helpers for tcal."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, Iterable, Mapping
from urllib.error import HTTPError, URLError
import urllib.request


DEFAULT_MODEL = "gpt-4o-mini"


@dataclass
class OpenAIResponse:
    content: str


class OpenAIAPIError(RuntimeError):
    """Raised when the OpenAI API returns an HTTP error."""

    def __init__(self, status_code: int, body: str) -> None:
        self.status_code = status_code
        self.body = body
        message = self._format_message(status_code, body)
        super().__init__(message)

    @staticmethod
    def _format_message(status_code: int, body: str) -> str:
        try:
            data = json.loads(body)
            err = data.get("error")
            if isinstance(err, dict):
                msg = err.get("message")
                if isinstance(msg, str) and msg:
                    return f"{status_code} {msg}"
        except Exception:  # noqa: BLE001
            pass
        snippet = (body or "Unknown error").strip()
        if len(snippet) > 200:
            snippet = snippet[:200] + "..."
        return f"{status_code} {snippet}"


class OpenAIClient:
    """Thin wrapper around OpenAI's chat API."""

    def __init__(self, api_key: str, model: str = DEFAULT_MODEL) -> None:
        self.api_key = api_key
        self.model = model

    def run_structured_prompt(
        self,
        messages: Iterable[Mapping[str, str]],
        *,
        response_format: Dict[str, Any],
        temperature: float = 0.0,
        max_completion_tokens: int = 512,
    ) -> OpenAIResponse:
        body = json.dumps(
            {
                "model": self.model,
                "messages": list(messages),
                "temperature": temperature,
                "max_completion_tokens": max_completion_tokens,
                "response_format": response_format,
            }
        ).encode("utf-8")

        req = urllib.request.Request(
            "https://api.openai.com/v1/chat/completions",
            data=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req) as resp:
                raw = resp.read().decode("utf-8")
        except HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
            raise OpenAIAPIError(exc.code, body) from exc
        except URLError as exc:
            raise RuntimeError(f"Network error calling OpenAI: {exc}") from exc

        try:
            data = json.loads(raw)
            content = data["choices"][0]["message"]["content"]
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(f"Invalid response from OpenAI: {exc}") from exc

        if not isinstance(content, str):
            raise RuntimeError("OpenAI response content missing")

        return OpenAIResponse(content=content)


__all__ = ["OpenAIClient", "OpenAIResponse", "DEFAULT_MODEL"]
