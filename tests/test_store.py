from datetime import datetime

from models import Event, JTBD, NorthStarMetrics
from store import load_events, save_events


def _make_event(ts: datetime, suffix: str) -> Event:
    return Event(
        bucket="thing",
        jtbd=JTBD(x=ts, y=f"Outcome {suffix}", z=f"Impact {suffix}"),
        nsm=NorthStarMetrics(p=6.0, q=7.0, r=5.5),
    )


def test_store_round_trip_persists_metrics(tmp_path) -> None:
    path = tmp_path / "events.csv"
    original = _make_event(datetime(2026, 3, 1, 12, 30), "A")

    save_events(path, [original])
    loaded = load_events(path)

    assert len(loaded) == 1
    recovered = loaded[0]

    assert recovered.jtbd == original.jtbd
    assert recovered.nsm.p == original.nsm.p
    assert recovered.nsm.r == original.nsm.r
