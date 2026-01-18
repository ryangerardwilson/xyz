#!/usr/bin/env python3
"""Configuration loading and path resolution for tcal."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

from paths import ensure_dir, xdg_config_home, xdg_data_home


@dataclass
class Config:
    data_parquet_path: Path
    editor: str


DEFAULT_DATA_FILENAME = "events.parquet"
DEFAULT_EDITOR = "vim"
CONFIG_FILENAME = "config.json"


def _default_data_path() -> Path:
    data_dir = Path(os.environ.get("XDG_DATA_HOME", xdg_data_home())) / "tcal"
    return data_dir / DEFAULT_DATA_FILENAME


def load_config() -> Config:
    """Load config from XDG path, falling back to defaults.

    Invalid JSON or missing file will fall back to defaults but keep the
    error message available to callers if needed.
    """

    config_path = (Path(xdg_config_home()) / "tcal" / CONFIG_FILENAME).expanduser()
    raw: Dict[str, Any] = {}

    if config_path.exists():
        try:
            raw = json.loads(config_path.read_text())
        except Exception:
            raw = {}

    data_path = Path(raw.get("data_parquet_path") or _default_data_path()).expanduser()
    editor = (raw.get("editor") or os.environ.get("EDITOR") or DEFAULT_EDITOR).strip()
    if not editor:
        editor = DEFAULT_EDITOR

    ensure_dir(data_path.parent)

    return Config(data_parquet_path=data_path, editor=editor)


__all__ = ["Config", "load_config", "CONFIG_FILENAME"]
