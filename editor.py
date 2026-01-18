#!/usr/bin/env python3
"""External editor flow for tcal."""
from __future__ import annotations

import json
import shlex
import subprocess
import tempfile
from pathlib import Path
from typing import List, Tuple

from models import Event, ValidationError, event_to_jsonable, normalize_event_payload


class EditorError(Exception):
    pass


def edit_event_via_editor(editor_cmd: str, seed_events: List[Event]) -> Tuple[bool, List[Event] | str]:
    """Launch external editor to edit/create one or more events.

    Returns (ok, Events_or_error_message)
    """
    payload = [event_to_jsonable(ev) for ev in seed_events]
    with tempfile.NamedTemporaryFile(mode="w+", suffix=".json", delete=False) as tmp:
        tmp_path = Path(tmp.name)
        json.dump(payload, tmp, indent=2)
        tmp.flush()
    try:
        cmd = shlex.split(editor_cmd) + [str(tmp_path)]
        proc = subprocess.run(cmd, check=False)
        if proc.returncode != 0:
            return False, "Editor cancelled or failed"
        try:
            data = json.loads(tmp_path.read_text())
            if isinstance(data, dict):
                data = [data]
            updated_events = [normalize_event_payload(item) for item in data]
            return True, updated_events
        except ValidationError as exc:
            return False, str(exc)
        except Exception as exc:  # noqa: BLE001
            return False, f"Invalid JSON: {exc}"
    finally:
        try:
            tmp_path.unlink()
        except Exception:
            pass


__all__ = ["edit_event_via_editor", "EditorError"]
