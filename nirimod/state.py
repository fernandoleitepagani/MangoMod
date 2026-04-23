

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from nirimod.kdl_parser import (
    NIRI_CONFIG,
    KdlNode,
    load_niri_config,
    load_niri_config_multi,
    parse_kdl,
    save_niri_config,
    save_niri_config_multi,
    write_kdl,
)
from nirimod.undo import UndoEntry, UndoManager

if TYPE_CHECKING:
    pass


@dataclass
class RuntimeInfo:

    niri_running: bool = False
    has_touchpad: bool = False


class AppState:

    def __init__(self) -> None:
        self._nodes: list[KdlNode] = []
        self._saved_kdl: str = ""
        self._undo: UndoManager = UndoManager()
        self._runtime: RuntimeInfo = RuntimeInfo()
        self._dirty: bool = False
        self._include_slots: list[tuple[KdlNode, Path]] = []
        self._source_files: set[Path] = set()

    def load(self) -> None:
        from nirimod import niri_ipc

        self._runtime = RuntimeInfo(
            niri_running=niri_ipc.is_niri_running(),
            has_touchpad=niri_ipc.has_touchpad(),
        )
        self._nodes, self._include_slots = load_niri_config_multi()
        self._source_files = {NIRI_CONFIG}
        for _, path in self._include_slots:
            if path.exists():
                self._source_files.add(path)
        self._saved_kdl = write_kdl(self._nodes) if self._nodes else ""
        self._dirty = False

    @property
    def nodes(self) -> list[KdlNode]:
        return self._nodes

    @nodes.setter
    def nodes(self, value: list[KdlNode]) -> None:
        self._nodes = value

    @property
    def saved_kdl(self) -> str:
        return self._saved_kdl

    @property
    def source_files(self) -> set[Path]:
        return self._source_files

    @property
    def include_slots(self) -> list[tuple[KdlNode, Path]]:
        return self._include_slots

    @property
    def is_multi_file(self) -> bool:
        return bool(self._include_slots)

    @property
    def niri_running(self) -> bool:
        return self._runtime.niri_running

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

    @property
    def undo(self) -> UndoManager:
        return self._undo

    def push_undo(self, description: str, before: str, after: str) -> None:
        self._undo.push(UndoEntry(description, before, after))

    def apply_undo(self) -> UndoEntry | None:
        entry = self._undo.pop_undo()
        if entry is None:
            return None
        self._nodes = parse_kdl(entry.snapshot_before)
        self._dirty = entry.snapshot_before != self._saved_kdl
        return entry

    def apply_redo(self) -> UndoEntry | None:
        entry = self._undo.pop_redo()
        if entry is None:
            return None
        self._nodes = parse_kdl(entry.snapshot_after)
        self._dirty = entry.snapshot_after != self._saved_kdl
        return entry

    def discard(self) -> None:
        self._nodes = parse_kdl(self._saved_kdl) if self._saved_kdl else []
        self._undo.clear()
        self._dirty = False

    def commit_save(self, new_kdl: str) -> None:
        self._saved_kdl = new_kdl
        self._undo.clear()
        self._dirty = False

    def reload_from_disk(self) -> None:
        self._nodes, self._include_slots = load_niri_config_multi()
        self._source_files = {NIRI_CONFIG}
        for _, path in self._include_slots:
            if path.exists():
                self._source_files.add(path)

    def write_current_kdl(self) -> str:
        return write_kdl(self._nodes)

    def write_to_path(self, path: Path | None = None) -> None:
        if path is not None:
            # Explicit path (e.g. validation temp file) — single file write
            save_niri_config(self._nodes, path=path)
        elif self._include_slots:
            save_niri_config_multi(self._nodes, self._include_slots)
        else:
            save_niri_config(self._nodes)
