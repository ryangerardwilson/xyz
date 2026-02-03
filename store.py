#!/usr/bin/env python3
"""CSV-backed storage for xyz events."""

from __future__ import annotations

import csv
import tempfile
from pathlib import Path
from typing import Iterable, List, Tuple, cast


from models import (
    DATETIME_FMT,
    Event,
    JTBD,
    NorthStarMetrics,
    BUCKETS,
    BucketName,
    parse_datetime,
)


CSV_HEADER = [
    "bucket",
    "x",
    "y",
    "z",
    "p",
    "q",
    "r",
]


class StorageError(Exception):
    pass


def _serialize_event(event: Event) -> List[str]:
    return [
        event.bucket,
        event.jtbd.x.strftime(DATETIME_FMT),
        event.jtbd.y,
        event.jtbd.z,
        str(event.nsm.p),
        str(event.nsm.q),
        str(event.nsm.r),
    ]


def _deserialize_row(row: List[str]) -> Event:
    if len(row) < len(CSV_HEADER):
        raise StorageError("Corrupt CSV row")
    (
        raw_bucket,
        dt_str,
        outcome,
        impact,
        p_str,
        q_str,
        r_str,
    ) = row[: len(CSV_HEADER)]

    bucket = raw_bucket.strip().lower()
    if bucket not in BUCKETS:
        raise StorageError(f"Invalid bucket '{bucket}' in storage")
    bucket_name = cast(BucketName, bucket)

    try:
        p_value = float(p_str)
        q_value = float(q_str)
        r_value = float(r_str)
    except ValueError as exc:
        raise StorageError("Stored metrics must be numeric") from exc

    return Event(
        bucket=bucket_name,
        jtbd=JTBD(
            x=parse_datetime(dt_str),
            y=outcome,
            z=impact,
        ),
        nsm=NorthStarMetrics(p=p_value, q=q_value, r=r_value),
    )


def load_events(path: Path) -> List[Event]:
    if not path.exists():
        return []
    try:
        with path.open(newline="", encoding="utf-8") as fh:
            reader = csv.reader(fh)
            events: List[Event] = []
            for row in reader:
                if not row or all(not cell.strip() for cell in row):
                    continue
                normalized = [cell.strip().lower() for cell in row]
                if (
                    len(normalized) >= len(CSV_HEADER)
                    and normalized[: len(CSV_HEADER)] == CSV_HEADER
                ):
                    # Skip header row
                    continue
                events.append(_deserialize_row(row))
    except Exception as exc:  # noqa: BLE001
        raise StorageError(f"Failed to read events from {path}: {exc}") from exc
    events.sort(key=lambda e: e.jtbd.x)
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
    ordered = sorted(
        events,
        key=lambda e: (
            e.jtbd.x,
            e.bucket,
            e.jtbd.y,
            e.jtbd.z,
            e.nsm.p,
            e.nsm.q,
            e.nsm.r,
        ),
    )
    rows = [CSV_HEADER] + [_serialize_event(e) for e in ordered]
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
                and e.bucket == original.bucket
                and e.jtbd.x == original.jtbd.x
                and e.jtbd.y == original.jtbd.y
                and e.jtbd.z == original.jtbd.z
                and e.nsm.p == original.nsm.p
                and e.nsm.q == original.nsm.q
                and e.nsm.r == original.nsm.r
            ):
                replaced = True
                continue
            updated.append(e)
    else:
        updated = list(events)
    updated.append(new_event)
    ordered = sorted(
        updated,
        key=lambda e: (
            e.jtbd.x,
            e.bucket,
            e.jtbd.y,
            e.jtbd.z,
            e.nsm.p,
            e.nsm.q,
            e.nsm.r,
        ),
    )
    save_events(path, ordered)
    return ordered


__all__ = ["load_events", "save_events", "upsert_event", "StorageError"]
