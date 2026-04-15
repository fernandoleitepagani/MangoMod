"""Named config profiles: save/load Niri config.kdl snapshots."""

from __future__ import annotations

import shutil
from pathlib import Path

from nirimod.kdl_parser import NIRI_CONFIG, PROFILES_DIR, save_niri_config


def list_profiles() -> list[str]:
    if not PROFILES_DIR.exists():
        return []
    return sorted(p.stem for p in PROFILES_DIR.glob("*.kdl"))


def save_profile(name: str) -> None:
    PROFILES_DIR.mkdir(parents=True, exist_ok=True)
    dest = PROFILES_DIR / f"{name}.kdl"
    if NIRI_CONFIG.exists():
        shutil.copy2(NIRI_CONFIG, dest)


def load_profile(name: str) -> bool:
    src = PROFILES_DIR / f"{name}.kdl"
    if not src.exists():
        return False
    from nirimod.kdl_parser import parse_kdl

    nodes = parse_kdl(src.read_text())
    save_niri_config(nodes)
    return True


def delete_profile(name: str) -> bool:
    p = PROFILES_DIR / f"{name}.kdl"
    if p.exists():
        p.unlink()
        return True
    return False


def profile_path(name: str) -> Path:
    return PROFILES_DIR / f"{name}.kdl"
