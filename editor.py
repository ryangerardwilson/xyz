#!/usr/bin/env python3
"""External editor flow for tcal."""
from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path
from typing import Tuple

from models import Event, ValidationError, event_to_jsonable, normalize_event_payload


class EditorError(Exception):
    pass


def edit_event_via_editor(editor_cmd: str, seed_event: Event) -> Tuple[bool, Event | str]:
    """Launch external editor to edit/create an event.

    Returns (ok, Event_or_error_message)
    """
    payload = event_to_jsonable(seed_event)
    with tempfile.NamedTemporaryFile(mode="w+", suffix=".json", delete=False) as tmp:
        tmp_path = Path(tmp.name)
        json.dump(payload, tmp, indent=2)
        tmp.flush()
    try:
        proc = subprocess.run([editor_cmd, str(tmp_path)], check=False)
        if proc.returncode != 0:
            return False, "Editor cancelled or failed"
        try:
            data = json.loads(tmp_path.read_text())
            updated = normalize_event_payload(data)
            return True, updated
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
