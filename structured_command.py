"""Parsing and formatting helpers for deterministic bucket/x/y/z commands."""

import re
from dataclasses import dataclass
from typing import Iterable, List

from models import (
    Event,
    JTBD,
    NorthStarMetrics,
    ValidationError,
    parse_datetime,
    BUCKETS,
    BucketName,
)


class StructuredCommandError(ValueError):
    """Raised when a deterministic command is malformed."""


STRUCTURED_TEMPLATE = (
    "bucket(<personal_development|thing|economic>) — "
    "when x(YYYY-MM-DD HH:MM:SS) happens, I want y(<outcome>) outcome, "
    "so I can z(<reason>); "
    "p(<alignment score>) q(<impact score>) r(<embodiment score>)"
)


@dataclass
class ParsedCommand:
    """Small helper to expose raw fields when needed."""

    bucket: BucketName
    x: str
    y: str
    z: str
    p: float
    q: float
    r: float


_COMPONENT_RE = re.compile(r"(?i){label}\((.*?)\)")


def _format_metric(value: float) -> str:
    text = f"{value:.2f}"
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text


def _extract_component(text: str, label: str) -> str:
    pattern = re.compile(rf"(?i){label}\\((.*?)\\)", re.DOTALL)
    match = pattern.search(text)
    if not match:
        raise StructuredCommandError(f"Missing {label}(...) block")
    return match.group(1).strip()


def parse_structured_command(text: str) -> Event:
    """Parse a single-line deterministic command into an Event."""

    if not text or not text.strip():
        raise StructuredCommandError("Command text is empty")

    bucket_raw = _extract_component(text, "bucket")
    x_raw = _extract_component(text, "x")
    y_raw = _extract_component(text, "y")
    z_raw = _extract_component(text, "z")
    p_raw = _extract_component(text, "p")
    q_raw = _extract_component(text, "q")
    r_raw = _extract_component(text, "r")

    if not y_raw:
        raise StructuredCommandError("y(...) must include an outcome description")

    bucket = bucket_raw.strip().lower()
    if not bucket:
        raise StructuredCommandError("bucket(...) cannot be empty")
    if bucket not in BUCKETS:
        valid = ", ".join(BUCKETS)
        raise StructuredCommandError(
            f"Invalid bucket '{bucket}'. Expected one of: {valid}"
        )

    try:
        dt = parse_datetime(x_raw)
    except ValidationError as exc:
        raise StructuredCommandError(str(exc)) from exc

    try:
        p_value = float(p_raw)
        q_value = float(q_raw)
        r_value = float(r_raw)
    except ValueError as exc:
        raise StructuredCommandError("North star metrics must be numeric") from exc

    return Event(
        bucket=bucket,  # type: ignore[arg-type]
        jtbd=JTBD(x=dt, y=y_raw, z=z_raw),
        nsm=NorthStarMetrics(p=p_value, q=q_value, r=r_value),
    )


def parse_structured_block(text: str) -> List[Event]:
    """Parse one or more deterministic commands from editor text."""

    entries = _split_entries(text)
    if not entries:
        return []

    events: List[Event] = []
    for idx, chunk in enumerate(entries, start=1):
        try:
            events.append(parse_structured_command(chunk))
        except StructuredCommandError as exc:
            raise StructuredCommandError(f"Entry {idx}: {exc}") from exc
    return events


def format_event_as_command(event: Event) -> str:
    """Render an Event using the deterministic template."""

    return (
        f"bucket({event.bucket}) — "
        f"when x({event.jtbd.x:%Y-%m-%d %H:%M:%S}) happens, "
        f"I want y({event.jtbd.y}) outcome, so I can z({event.jtbd.z}); "
        f"p({_format_metric(event.nsm.p)}) "
        f"q({_format_metric(event.nsm.q)}) "
        f"r({_format_metric(event.nsm.r)})"
    )


def format_events_block(events: Iterable[Event]) -> str:
    """Render multiple events separated by blank lines."""

    lines = [format_event_as_command(ev) for ev in events]
    return "\n\n".join(lines)


def _split_entries(text: str) -> List[str]:
    entries: List[str] = []
    current: List[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            if current:
                entries.append(" ".join(current))
                current = []
            continue
        current.append(stripped)
    if current:
        entries.append(" ".join(current))
    return entries


__all__ = [
    "StructuredCommandError",
    "STRUCTURED_TEMPLATE",
    "ParsedCommand",
    "parse_structured_command",
    "parse_structured_block",
    "format_event_as_command",
    "format_events_block",
]
