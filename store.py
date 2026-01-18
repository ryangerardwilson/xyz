#!/usr/bin/env python3
"""PyArrow-backed storage for tcal events."""
from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Iterable, List, Tuple

import pyarrow as pa
import pyarrow.parquet as pq

from models import Event, ValidationError


_SCHEMA = pa.schema(
    [
        ("datetime", pa.timestamp("ns")),
        ("event", pa.string()),
        ("details", pa.string()),
    ]
)


class StorageError(Exception):
    pass


def _events_to_table(events: Iterable[Event]) -> pa.Table:
    dts = [e.datetime for e in events]
    evs = [e.event for e in events]
    dets = [e.details for e in events]
    return pa.Table.from_pydict(
        {
            "datetime": dts,
            "event": evs,
            "details": dets,
        },
        schema=_SCHEMA,
    )


def _table_to_events(table: pa.Table) -> List[Event]:
    # Validate schema shape explicitly
    if table.schema != _SCHEMA:
        raise StorageError("Parquet schema mismatch for events.parquet")
    dts = table.column("datetime").to_pylist()
    evs = table.column("event").to_pylist()
    dets = table.column("details").to_pylist()
    events: List[Event] = []
    for dt, ev, det in zip(dts, evs, dets):
        events.append(Event(datetime=dt, event=ev, details=det))
    events.sort(key=lambda e: e.datetime)
    return events


def load_events(path: Path) -> List[Event]:
    if not path.exists():
        return []
    try:
        table = pq.read_table(path)
        return _table_to_events(table)
    except StorageError:
        raise
    except Exception as exc:
        raise StorageError(f"Failed to read events from {path}: {exc}") from exc


def _write_atomic(path: Path, table: pa.Table) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=str(path.parent), delete=False) as tmp:
        tmp_path = Path(tmp.name)
    try:
        pq.write_table(table, tmp_path)
        tmp_path.replace(path)
    finally:
        if tmp_path.exists():
            try:
                os.remove(tmp_path)
            except OSError:
                pass


def save_events(path: Path, events: Iterable[Event]) -> None:
    seen = set()
    ordered: List[Event] = []
    for e in events:
        if e.datetime in seen:
            raise ValidationError("Duplicate datetime detected")
        seen.add(e.datetime)
        ordered.append(e)
    ordered.sort(key=lambda e: e.datetime)
    table = _events_to_table(ordered)
    _write_atomic(path, table)


def upsert_event(path: Path, events: List[Event], new_event: Event, *, replace_dt: Tuple[bool, Event | None] = (False, None)) -> List[Event]:
    """Insert or update an event.

    replace_dt: (is_editing, original_event)
      - If editing and datetime changes, ensure we drop the old datetime before duplicate check.
    """
    editing, original = replace_dt
    updated: List[Event] = []
    target_old_dt = original.datetime if (editing and original is not None) else None
    for e in events:
        if target_old_dt is not None and e.datetime == target_old_dt:
            continue
        updated.append(e)
    # Check duplicate against remaining
    if any(e.datetime == new_event.datetime for e in updated):
        raise ValidationError("An event already exists at that datetime")
    updated.append(new_event)
    save_events(path, updated)
    return updated


__all__ = [
    "load_events",
    "save_events",
    "upsert_event",
    "StorageError",
]
