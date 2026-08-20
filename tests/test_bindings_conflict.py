"""Tests for keybinding duplicate and conflict detection."""

from __future__ import annotations

import unittest
import pytest

pytest.importorskip("gi")

from nirimod.pages.bindings import _make_bind, find_binding_conflicts


class TestBindingConflicts(unittest.TestCase):
    def test_no_conflicts_on_unique_binds(self):
        binds = [
            _make_bind("Mod+Return", "spawn", ["alacritty"]),
            _make_bind("Mod+Q", "close-window"),
            _make_bind("Mod+Shift+E", "quit"),
        ]
        conflicts = find_binding_conflicts(binds)
        self.assertEqual(conflicts, set())

    def test_detects_duplicate_keysyms(self):
        binds = [
            _make_bind("Mod+Return", "spawn", ["alacritty"]),
            _make_bind("Mod+Return", "spawn", ["foot"]),
            _make_bind("Mod+Q", "close-window"),
            _make_bind("Mod+Q", "spawn", ["rofi"]),
        ]
        conflicts = find_binding_conflicts(binds)
        self.assertEqual(conflicts, {"Mod+Return", "Mod+Q"})
