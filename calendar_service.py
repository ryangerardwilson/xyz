#!/usr/bin/env python3
"""Calendar-focused data helpers for tcal."""

from __future__ import annotations

from pathlib import Path
from typing import List, Tuple

from models import Event
from store import StorageError, load_events, upsert_event


class CalendarService:
    """Wrapper around persistent calendar storage operations."""

    def __init__(self, data_path: Path) -> None:
        self._data_path = data_path

    @property
    def data_path(self) -> Path:
        return self._data_path

    def load_events(self) -> List[Event]:
        """Load all events from storage."""
        return load_events(self._data_path)

    def upsert_event(
        self,
        events: List[Event],
        new_event: Event,
        *,
        replace_dt: Tuple[bool, Event | None] = (False, None),
    ) -> List[Event]:
        """Insert or update an event and return the updated list."""
        return upsert_event(
            self._data_path,
            events,
            new_event,
            replace_dt=replace_dt,
        )


__all__ = ["CalendarService", "StorageError"]
