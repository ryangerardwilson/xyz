#!/usr/bin/env python3
"""Date range helpers for calendar queries."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Optional


@dataclass(frozen=True)
class DateRange:
    start: Optional[datetime]
    end: Optional[datetime]


def _start_of_day(day: date) -> datetime:
    return datetime.combine(day, datetime.min.time())


def _end_of_day(day: date) -> datetime:
    return datetime.combine(day, datetime.max.time().replace(microsecond=0))


def _start_of_week(day: date) -> date:
    return day - timedelta(days=day.weekday())


def _end_of_week(day: date) -> date:
    return _start_of_week(day) + timedelta(days=6)


def _start_of_month(day: date) -> date:
    return day.replace(day=1)


def _end_of_month(day: date) -> date:
    next_month = (day.replace(day=28) + timedelta(days=4)).replace(day=1)
    return next_month - timedelta(days=1)


def resolve_date_range(kind: str, *, today: Optional[date] = None) -> DateRange:
    today = today or date.today()

    mapping = {
        "day_before_yesterday": today - timedelta(days=2),
        "yesterday": today - timedelta(days=1),
        "today": today,
        "tomorrow": today + timedelta(days=1),
    }

    if kind in mapping:
        target = mapping[kind]
        return DateRange(_start_of_day(target), _end_of_day(target))

    if kind == "this_week":
        start = _start_of_week(today)
        end = _end_of_week(today)
        return DateRange(_start_of_day(start), _end_of_day(end))

    if kind == "this_month":
        start = _start_of_month(today)
        end = _end_of_month(today)
        return DateRange(_start_of_day(start), _end_of_day(end))

    if kind == "next_month":
        next_month_start = (_end_of_month(today) + timedelta(days=1)).replace(day=1)
        end = _end_of_month(next_month_start)
        return DateRange(_start_of_day(next_month_start), _end_of_day(end))

    if kind == "last_month":
        prev_month_end = _start_of_month(today) - timedelta(days=1)
        start = _start_of_month(prev_month_end)
        return DateRange(_start_of_day(start), _end_of_day(prev_month_end))

    if kind == "this_year":
        start = today.replace(month=1, day=1)
        end = today.replace(month=12, day=31)
        return DateRange(_start_of_day(start), _end_of_day(end))

    if kind == "all":
        return DateRange(start=None, end=None)

    raise ValueError(f"Unknown date range kind: {kind}")


__all__ = ["DateRange", "resolve_date_range"]
