#!/usr/bin/env python3
"""CSV-backed storage for tcal events."""

from __future__ import annotations

import csv
import tempfile
from pathlib import Path
from typing import Iterable, List, Tuple


from models import DATETIME_FMT, Event


class StorageError(Exception):
    pass


def _serialize_event(event: Event) -> List[str]:
    return [event.datetime.strftime(DATETIME_FMT), event.event, event.details]


def _deserialize_row(row: List[str]) -> Event:
    if len(row) < 3:
        raise StorageError("Corrupt CSV row")
    dt_str, event_name, details = row[0], row[1], row[2]
    from models import parse_datetime

    return Event(datetime=parse_datetime(dt_str), event=event_name, details=details)


def load_events(path: Path) -> List[Event]:
    if not path.exists():
        return []
    try:
        with path.open(newline="", encoding="utf-8") as fh:
            reader = csv.reader(fh)
            events = [_deserialize_row(row) for row in reader]
    except Exception as exc:  # noqa: BLE001
        raise StorageError(f"Failed to read events from {path}: {exc}") from exc
    events.sort(key=lambda e: e.datetime)
    return events


def _write_atomic(path: Path, rows: Iterable[List[str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", newline="", delete=False, encoding="utf-8", dir=str(path.parent)
    ) as tmp:
        tmp_path = Path(tmp.name)
        writer = csv.writer(tmp)
        for row in rows:
            writer.writerow(row)
    tmp_path.replace(path)


def save_events(path: Path, events: Iterable[Event]) -> None:
    ordered = sorted(events, key=lambda e: (e.datetime, e.event, e.details))
    rows = [_serialize_event(e) for e in ordered]
    _write_atomic(path, rows)


def upsert_event(
    path: Path,
    events: List[Event],
    new_event: Event,
    *,
    replace_dt: Tuple[bool, Event | None] = (False, None),
) -> List[Event]:
    editing, original = replace_dt
    updated: List[Event] = []
    replaced = False
    if editing and original is not None:
        for e in events:
            if (
                not replaced
                and e.datetime == original.datetime
                and e.event == original.event
                and e.details == original.details
            ):
                replaced = True
                continue
            updated.append(e)
    else:
        updated = list(events)
    updated.append(new_event)
    save_events(path, updated)
    return updated


__all__ = ["load_events", "save_events", "upsert_event", "StorageError"]
