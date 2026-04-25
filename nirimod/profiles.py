"""Named config profiles: save/load Niri config snapshots."""

from __future__ import annotations

import shutil
from pathlib import Path

from nirimod.kdl_parser import NIRI_CONFIG, PROFILES_DIR, save_niri_config


def list_profiles() -> list[str]:
    if not PROFILES_DIR.exists():
        return []
    names = [p.stem for p in PROFILES_DIR.glob("*.kdl")]
    names += [p.name for p in PROFILES_DIR.iterdir() if p.is_dir()]
    return sorted(names)


def save_profile(name: str, source_files: set[Path] | None = None) -> None:
    PROFILES_DIR.mkdir(parents=True, exist_ok=True)

    if source_files and len(source_files) > 1:
        dest_dir = PROFILES_DIR / name
        dest_dir.mkdir(exist_ok=True)
        for p in source_files:
            if p.exists():
                try:
                    rel = p.relative_to(NIRI_CONFIG.parent)
                    dest = dest_dir / rel
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(p, dest)
                except ValueError:
                    shutil.copy2(p, dest_dir / p.name)
    else:
        if NIRI_CONFIG.exists():
            shutil.copy2(NIRI_CONFIG, PROFILES_DIR / f"{name}.kdl")


def load_profile(name: str) -> bool:
    dir_profile = PROFILES_DIR / name
    if dir_profile.is_dir():
        def _restore(src_dir, dest_dir):
            for f in src_dir.iterdir():
                if f.is_file():
                    rel = f.relative_to(dir_profile)
                    target = dest_dir / rel
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(f, target)
                elif f.is_dir():
                    _restore(f, dest_dir)
                    
        _restore(dir_profile, NIRI_CONFIG.parent)
        return True

    src = PROFILES_DIR / f"{name}.kdl"
    if not src.exists():
        return False
    from nirimod.kdl_parser import parse_kdl
    save_niri_config(parse_kdl(src.read_text()))
    return True


def delete_profile(name: str) -> bool:
    dir_profile = PROFILES_DIR / name
    if dir_profile.is_dir():
        shutil.rmtree(dir_profile)
        return True
    p = PROFILES_DIR / f"{name}.kdl"
    if p.exists():
        p.unlink()
        return True
    return False


def profile_path(name: str) -> Path:
    return PROFILES_DIR / name
