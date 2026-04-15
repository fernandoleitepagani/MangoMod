"""Application state manager."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from nirimod.kdl_parser import (
    KdlNode,
    load_niri_config,
    parse_kdl,
    save_niri_config,
    write_kdl,
)
from nirimod.undo import UndoEntry, UndoManager

if TYPE_CHECKING:
    from pathlib import Path


@dataclass
class RuntimeInfo:
    """Immutable facts about the runtime environment, detected once at startup."""

    niri_running: bool = False
    has_touchpad: bool = False


class AppState:
    """Central state container for the NiriMod application.

    Holds the parsed KDL node tree, the last-saved KDL text snapshot,
    runtime environment metadata, and the undo/redo stack. All mutations
    to the config must go through this class so the rest of the application
    can remain stateless with respect to config management.
    """

    def __init__(self) -> None:
        self._nodes: list[KdlNode] = []
        self._saved_kdl: str = ""
        self._undo: UndoManager = UndoManager()
        self._runtime: RuntimeInfo = RuntimeInfo()
        self._dirty: bool = False

    # Initialization

    def load(self) -> None:
        """Load config from disk and detect runtime environment.

        Called once at application startup. Detects whether niri is running
        and whether a touchpad is present, then parses the config file.
        """
        from nirimod import niri_ipc

        self._runtime = RuntimeInfo(
            niri_running=niri_ipc.is_niri_running(),
            has_touchpad=niri_ipc.has_touchpad(),
        )
        self._nodes = load_niri_config()
        self._saved_kdl = write_kdl(self._nodes) if self._nodes else ""
        self._dirty = False

    # Config node access

    @property
    def nodes(self) -> list[KdlNode]:
        """The current (possibly dirty) parsed KDL node tree."""
        return self._nodes

    @nodes.setter
    def nodes(self, value: list[KdlNode]) -> None:
        self._nodes = value

    @property
    def saved_kdl(self) -> str:
        """The KDL text of the last successfully saved state."""
        return self._saved_kdl

    # Runtime info

    @property
    def niri_running(self) -> bool:
        return self._runtime.niri_running

    @property
    def has_touchpad(self) -> bool:
        return self._runtime.has_touchpad

    # Dirty tracking

    @property
    def is_dirty(self) -> bool:
        return self._dirty

    def mark_dirty(self) -> None:
        self._dirty = True

    def mark_clean(self) -> None:
        self._dirty = False

    # Undo / redo

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
        self._dirty = bool(self._nodes)
        return entry

    def apply_redo(self) -> UndoEntry | None:
        entry = self._undo.pop_redo()
        if entry is None:
            return None
        self._nodes = parse_kdl(entry.snapshot_after)
        self._dirty = True
        return entry

    def discard(self) -> None:
        """Revert nodes to the last saved snapshot and clear undo history."""
        self._nodes = parse_kdl(self._saved_kdl) if self._saved_kdl else []
        self._undo.clear()
        self._dirty = False

    # Persistence

    def commit_save(self, new_kdl: str) -> None:
        """Record a successful save: update the saved snapshot and clear undo."""
        self._saved_kdl = new_kdl
        self._undo.clear()
        self._dirty = False

    def reload_from_disk(self) -> None:
        """Re-parse the config file from disk into the node tree."""
        self._nodes = load_niri_config()

    def write_current_kdl(self) -> str:
        """Serialize the current node tree to a KDL string."""
        return write_kdl(self._nodes)

    def write_to_path(self, path: Path | None = None) -> None:
        """Write the current node tree to a file path (defaults to NIRI_CONFIG)."""
        save_niri_config(self._nodes, path=path)
