from __future__ import annotations

import json
import os
from pathlib import Path

_SETTINGS_DIR = Path(os.path.expanduser("~/.config/nirimod"))
_SETTINGS_FILE = _SETTINGS_DIR / "settings.json"

_DEFAULTS: dict = {
    "auto_update": True,
}

_cache: dict | None = None


def _load() -> dict:
    global _cache
    if _cache is not None:
        return _cache
    if _SETTINGS_FILE.exists():
        try:
            data = json.loads(_SETTINGS_FILE.read_text())
            _cache = {**_DEFAULTS, **data}
            return _cache
        except Exception:
            pass
    _cache = dict(_DEFAULTS)
    return _cache


def _save(data: dict):
    global _cache
    _SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
    _SETTINGS_FILE.write_text(json.dumps(data, indent=2))
    _cache = data


def get(key: str, default=None):
    return _load().get(key, default)


def set(key: str, value):  # noqa: A001
    data = dict(_load())
    data[key] = value
    _save(data)
