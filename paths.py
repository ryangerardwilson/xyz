#!/usr/bin/env python3
"""XDG path helpers for xyz."""

from __future__ import annotations

import os
from pathlib import Path


def xdg_config_home() -> Path:
    return Path(os.environ.get("XDG_CONFIG_HOME", "~/.config")).expanduser()


def xdg_data_home() -> Path:
    return Path(os.environ.get("XDG_DATA_HOME", "~/.xyz")).expanduser()


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


__all__ = ["xdg_config_home", "xdg_data_home", "ensure_dir"]
