"""Named config profiles: save/load Niri config snapshots."""

from __future__ import annotations

import shutil
from pathlib import Path

from nirimod import kdl_parser


def list_profiles() -> list[str]:
    if not kdl_parser.PROFILES_DIR.exists():
        return []
    names = [p.stem for p in kdl_parser.PROFILES_DIR.glob("*.kdl")]
    names += [p.name for p in kdl_parser.PROFILES_DIR.iterdir() if p.is_dir()]
    return sorted(names)


def save_profile(name: str, source_files: set[Path] | None = None) -> None:
    kdl_parser.PROFILES_DIR.mkdir(parents=True, exist_ok=True)

    if source_files and len(source_files) > 1:
        dest_dir = kdl_parser.PROFILES_DIR / name
        dest_dir.mkdir(exist_ok=True)
        for p in source_files:
            if p.exists():
                try:
                    rel = p.relative_to(kdl_parser.NIRI_CONFIG.parent)
                    dest = dest_dir / rel
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(p, dest)
                except ValueError:
                    shutil.copy2(p, dest_dir / p.name)
    else:
        if kdl_parser.NIRI_CONFIG.exists():
            shutil.copy2(kdl_parser.NIRI_CONFIG, kdl_parser.PROFILES_DIR / f"{name}.kdl")


def load_profile(name: str) -> bool:
    dir_profile = kdl_parser.PROFILES_DIR / name
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
                    
        _restore(dir_profile, kdl_parser.NIRI_CONFIG.parent)
        return True

    src = kdl_parser.PROFILES_DIR / f"{name}.kdl"
    if not src.exists():
        return False
    kdl_parser.save_niri_config(kdl_parser.parse_kdl(src.read_text()))
    return True


def delete_profile(name: str) -> bool:
    dir_profile = kdl_parser.PROFILES_DIR / name
    if dir_profile.is_dir():
        shutil.rmtree(dir_profile)
        return True
    p = kdl_parser.PROFILES_DIR / f"{name}.kdl"
    if p.exists():
        p.unlink()
        return True
    return False

