from datetime import datetime

import pytest

from models import (
    event_to_jsonable,
    normalize_event_payload,
    ValidationError,
)


def _sample_payload() -> dict:
    return {
        "bucket": "personal_development",
        "jtbd": {
            "x": "2026-02-10 09:00:00",
            "y": "publish onboarding playbook",
            "z": "scale cohort success",
        },
        "nsm": {
            "p": "7.5",
            "q": "8",
            "r": "6.5",
        },
    }


def test_normalize_event_payload_creates_event() -> None:
    payload = _sample_payload()
    event = normalize_event_payload(payload)

    assert event.bucket == "personal_development"
    assert event.jtbd.y == "publish onboarding playbook"
    assert event.jtbd.x == datetime(2026, 2, 10, 9, 0)
    assert event.nsm.p == pytest.approx(7.5)
    assert event.nsm.r == pytest.approx(6.5)

    jsonable = event_to_jsonable(event)
    assert jsonable["nsm"]["q"] == pytest.approx(8)


def test_normalize_event_payload_rejects_non_numeric_metrics() -> None:
    payload = _sample_payload()
    payload["nsm"]["q"] = "not-a-number"

    with pytest.raises(ValidationError):
        normalize_event_payload(payload)
