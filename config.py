#!/usr/bin/env python3
"""Configuration loading and path resolution for tcal."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

from paths import ensure_dir, xdg_config_home


@dataclass
class Config:
    data_csv_path: Path
    openai_api_key: Optional[str]


DEFAULT_DATA_FILENAME = "event.csv"
CONFIG_FILENAME = "config.json"


def _default_data_path() -> Path:
    xdg_data_env = os.environ.get("XDG_DATA_HOME")
    if xdg_data_env:
        data_dir = Path(xdg_data_env) / "tcal"
    else:
        data_dir = Path("~/.tcal")
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

    data_path = Path(raw.get("data_csv_path") or _default_data_path()).expanduser()
    openai_api_key = raw.get("openai_api_key")

    ensure_dir(data_path.parent)

    return Config(data_csv_path=data_path, openai_api_key=openai_api_key)


__all__ = ["Config", "load_config", "CONFIG_FILENAME"]
