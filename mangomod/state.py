from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from mangomod.mango_config import MangoConfig, load_config


@dataclass
class RuntimeInfo:
    mango_running: bool = False
    has_touchpad: bool = False


class AppState:
    def __init__(self) -> None:
        self._config = MangoConfig()
        self._saved_snapshot: dict[Path, str] = {}
        self._runtime = RuntimeInfo()
        self._dirty = False
        self._cached_snapshot: dict[Path, str] | None = None

    def load(self) -> None:
        from mangomod import mango_ipc

        self._runtime = RuntimeInfo(
            mango_running=mango_ipc.is_running(),
            has_touchpad=_detect_touchpad(),
        )
        self._config = load_config()
        self._saved_snapshot = self.snapshot()
        self._cached_snapshot = None
        self._dirty = False

    @property
    def config(self) -> MangoConfig:
        return self._config

    @property
    def mango_running(self) -> bool:
        return self._runtime.mango_running

    @property
    def has_touchpad(self) -> bool:
        return self._runtime.has_touchpad

    @property
    def is_dirty(self) -> bool:
        return self._dirty

    def mark_dirty(self) -> None:
        self._dirty = True

    def mark_clean(self) -> None:
        self._dirty = False

    def invalidate_cache(self) -> None:
        """Called by pages after mutating the config."""
        self._cached_snapshot = None

    def snapshot(self) -> dict[Path, str]:
        return {p: self._config.write_file(p) for p in self._config.all_files()}

    def is_clean(self) -> bool:
        if self._cached_snapshot is None:
            self._cached_snapshot = self.snapshot()
        return self._cached_snapshot == self._saved_snapshot

    def disk_snapshot(self) -> dict[Path, str | None]:
        return {
            p: (p.read_text() if p.exists() else None)
            for p in self._config.all_files()
        }

    def restore_disk(self, snapshot: dict[Path, str | None]) -> None:
        for path, content in snapshot.items():
            if content is None:
                try:
                    path.unlink(missing_ok=True)
                except OSError:
                    pass
            else:
                path.parent.mkdir(parents=True, exist_ok=True)
                try:
                    path.write_text(content)
                except OSError:
                    pass

    def commit_save(self, snapshot: dict[Path, str]) -> None:
        self._saved_snapshot = snapshot
        self._cached_snapshot = None
        self._dirty = False

    def discard(self) -> None:
        self.load()

    def write_current_config(self) -> str:
        return self._config.write()

    def write_to_path(self, path: Path | None = None) -> None:
        if path is not None:
            from mangomod.mango_config import _atomic_write

            _atomic_write(path, self._config.write())
        else:
            self._config.write_all()


def _detect_touchpad() -> bool:
    try:
        for dev in os.listdir("/sys/class/input"):
            nf = f"/sys/class/input/{dev}/device/name"
            if os.path.exists(nf):
                with open(nf) as fh:
                    name = fh.read().lower()
                if "touchpad" in name or "trackpad" in name:
                    return True
    except OSError:
        pass
    return False
