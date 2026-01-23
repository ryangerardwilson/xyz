#!/usr/bin/env python3
"""Core models and validation helpers for xyz."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Literal, Sequence

DATETIME_FMT = "%Y-%m-%d %H:%M:%S"


BucketName = Literal["personal_development", "thing", "economic"]
BUCKETS: Sequence[BucketName] = (
    "personal_development",
    "thing",
    "economic",
)
ALL_BUCKET = "all"
DEFAULT_BUCKET: BucketName = "personal_development"


@dataclass
class Coordinates:
    x: datetime
    y: str
    z: str

    def with_updated(
        self,
        *,
        x: Optional[datetime] = None,
        y: Optional[str] = None,
        z: Optional[str] = None,
    ) -> "Coordinates":
        return Coordinates(
            x=x if x is not None else self.x,
            y=y if y is not None else self.y,
            z=z if z is not None else self.z,
        )


@dataclass
class Event:
    bucket: BucketName
    coords: Coordinates

    def with_updated(
        self,
        *,
        bucket: Optional[BucketName] = None,
        x: Optional[datetime] = None,
        y: Optional[str] = None,
        z: Optional[str] = None,
    ) -> "Event":
        return Event(
            bucket=bucket if bucket is not None else self.bucket,
            coords=self.coords.with_updated(x=x, y=y, z=z),
        )


class ValidationError(Exception):
    pass


def parse_datetime(value: str) -> datetime:
    value = value.strip()

    # Accept ISO-8601 formats like YYYY-MM-DDTHH:MM[:SS][Z]
    iso_candidate = value
    if iso_candidate.endswith("Z"):
        iso_candidate = iso_candidate[:-1]
    iso_candidate = iso_candidate.replace("T", " ")
    try:
        return datetime.fromisoformat(iso_candidate)
    except ValueError:
        pass

    # Accept YYYY-MM-DD HH:MM and normalize seconds
    try:
        if len(value) == 16 and "T" not in value:  # YYYY-MM-DD HH:MM
            value = f"{value}:00"
        return datetime.strptime(value, DATETIME_FMT)
    except ValueError as exc:
        raise ValidationError(
            f"Invalid datetime format: '{value}'. Expected YYYY-MM-DD HH:MM[:SS]"
        ) from exc


def _normalize_bucket(raw_bucket: object | None) -> BucketName:
    if raw_bucket is None:
        raise ValidationError("Missing 'bucket' field")
    bucket = str(raw_bucket).strip().lower()
    if bucket not in BUCKETS:
        valid = ", ".join(BUCKETS)
        raise ValidationError(f"Invalid bucket '{bucket}'. Expected one of: {valid}")
    return bucket  # type: ignore[return-value]


def normalize_event_payload(data: dict) -> Event:
    bucket = _normalize_bucket(data.get("bucket"))

    coords_data = data.get("coordinates")
    if not isinstance(coords_data, dict):
        raise ValidationError("Missing 'coordinates' object with x/y/z")

    x_value = coords_data.get("x")
    y_value = coords_data.get("y")
    z_value = coords_data.get("z")

    if x_value is None or y_value is None or z_value is None:
        raise ValidationError("Coordinates must include 'x', 'y', and 'z'")

    dt = parse_datetime(str(x_value))
    outcome = str(y_value).strip()
    if not outcome:
        raise ValidationError("'y' (outcome) cannot be empty")

    impact = str(z_value).strip()
    if not impact:
        raise ValidationError("'z' (impact) cannot be empty")

    return Event(bucket=bucket, coords=Coordinates(x=dt, y=outcome, z=impact))


def event_to_jsonable(event: Event) -> dict:
    return {
        "bucket": event.bucket,
        "coordinates": {
            "x": event.coords.x.strftime(DATETIME_FMT),
            "y": event.coords.y,
            "z": event.coords.z,
        },
    }


__all__ = [
    "Event",
    "Coordinates",
    "ValidationError",
    "parse_datetime",
    "normalize_event_payload",
    "event_to_jsonable",
    "DATETIME_FMT",
    "BucketName",
    "BUCKETS",
    "ALL_BUCKET",
    "DEFAULT_BUCKET",
]
