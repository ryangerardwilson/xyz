#!/usr/bin/env python3
"""Configuration loading and path resolution for xyz."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

from paths import ensure_dir, xdg_config_home


@dataclass
class Config:
    data_csv_path: Path


DEFAULT_DATA_FILENAME = "event.csv"
CONFIG_FILENAME = "config.json"


def _default_data_path() -> Path:
    xdg_data_env = os.environ.get("XDG_DATA_HOME")
    if xdg_data_env:
        data_dir = Path(xdg_data_env) / "xyz"
    else:
        data_dir = Path("~/.xyz")
    return data_dir / DEFAULT_DATA_FILENAME


def load_config() -> Config:
    """Load config from XDG path, falling back to defaults.

    Invalid JSON or missing file will fall back to defaults but keep the
    error message available to callers if needed.
    """

    config_path = (Path(xdg_config_home()) / "xyz" / CONFIG_FILENAME).expanduser()
    raw: Dict[str, Any] = {}

    if config_path.exists():
        raw_text = config_path.read_text()
        try:
            raw = json.loads(raw_text)
        except json.JSONDecodeError:
            raw = json.loads(_strip_trailing_commas(raw_text))
        except Exception:
            raw = {}

    data_path = Path(raw.get("data_csv_path") or _default_data_path()).expanduser()

    ensure_dir(data_path.parent)

    return Config(
        data_csv_path=data_path,
    )


def _strip_trailing_commas(text: str) -> str:
    """Remove trailing commas before closing braces/brackets."""
    return re.sub(r",(\s*[}\]])", r"\1", text)


__all__ = ["Config", "load_config", "CONFIG_FILENAME"]
