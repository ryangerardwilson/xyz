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
class JTBD:
    x: datetime
    y: str
    z: str

    def with_updated(
        self,
        *,
        x: Optional[datetime] = None,
        y: Optional[str] = None,
        z: Optional[str] = None,
    ) -> "JTBD":
        return JTBD(
            x=x if x is not None else self.x,
            y=y if y is not None else self.y,
            z=z if z is not None else self.z,
        )


@dataclass
class NorthStarMetrics:
    p: float
    q: float
    r: float

    def with_updated(
        self,
        *,
        p: Optional[float] = None,
        q: Optional[float] = None,
        r: Optional[float] = None,
    ) -> "NorthStarMetrics":
        return NorthStarMetrics(
            p=p if p is not None else self.p,
            q=q if q is not None else self.q,
            r=r if r is not None else self.r,
        )


@dataclass
class Event:
    bucket: BucketName
    jtbd: JTBD
    nsm: NorthStarMetrics

    def with_updated(
        self,
        *,
        bucket: Optional[BucketName] = None,
        x: Optional[datetime] = None,
        y: Optional[str] = None,
        z: Optional[str] = None,
        p: Optional[float] = None,
        q: Optional[float] = None,
        r: Optional[float] = None,
    ) -> "Event":
        return Event(
            bucket=bucket if bucket is not None else self.bucket,
            jtbd=self.jtbd.with_updated(x=x, y=y, z=z),
            nsm=self.nsm.with_updated(p=p, q=q, r=r),
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


def _extract_jtbd(data: dict) -> JTBD:
    jtbd_data = data.get("jtbd")
    if not isinstance(jtbd_data, dict):
        raise ValidationError("Missing 'jtbd' object with x/y/z")

    x_value = jtbd_data.get("x")
    y_value = jtbd_data.get("y")
    z_value = jtbd_data.get("z")

    if x_value is None or y_value is None or z_value is None:
        raise ValidationError("JTBD must include 'x', 'y', and 'z'")

    dt = parse_datetime(str(x_value))
    outcome = str(y_value).strip()
    if not outcome:
        raise ValidationError("'y' (outcome) cannot be empty")

    impact = str(z_value).strip()
    if not impact:
        raise ValidationError("'z' (impact) cannot be empty")

    return JTBD(x=dt, y=outcome, z=impact)


def _coerce_metric(value: object, label: str) -> float:
    if value is None:
        raise ValidationError(f"Missing metric '{label}'")
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        candidate = value.strip()
        if not candidate:
            raise ValidationError(f"Metric '{label}' cannot be empty")
        try:
            return float(candidate)
        except ValueError as exc:
            raise ValidationError(f"Metric '{label}' must be numeric") from exc
    raise ValidationError(f"Metric '{label}' must be numeric")


def _extract_nsm(data: dict) -> NorthStarMetrics:
    nsm_data = data.get("nsm")
    if not isinstance(nsm_data, dict):
        raise ValidationError("Missing 'nsm' object with p/q/r")

    p_value = _coerce_metric(nsm_data.get("p"), "p")
    q_value = _coerce_metric(nsm_data.get("q"), "q")
    r_value = _coerce_metric(nsm_data.get("r"), "r")

    return NorthStarMetrics(p=p_value, q=q_value, r=r_value)


def normalize_event_payload(data: dict) -> Event:
    bucket = _normalize_bucket(data.get("bucket"))
    jtbd = _extract_jtbd(data)
    nsm = _extract_nsm(data)
    return Event(bucket=bucket, jtbd=jtbd, nsm=nsm)


def event_to_jsonable(event: Event) -> dict:
    return {
        "bucket": event.bucket,
        "jtbd": {
            "x": event.jtbd.x.strftime(DATETIME_FMT),
            "y": event.jtbd.y,
            "z": event.jtbd.z,
        },
        "nsm": {
            "p": event.nsm.p,
            "q": event.nsm.q,
            "r": event.nsm.r,
        },
    }


__all__ = [
    "Event",
    "JTBD",
    "NorthStarMetrics",
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
