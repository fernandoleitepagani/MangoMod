"""Tests for input page configuration helpers."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock
import pytest

pytest.importorskip("gi")

from nirimod.kdl_parser import KdlNode, find_or_create, parse_kdl, write_kdl
from nirimod.pages.input_page import ACCEL_PROFILES, InputPage


class DummyWindow:
    def __init__(self, nodes: list[KdlNode]):
        self._nodes = nodes
        self.app_state = MagicMock()
        self.app_state.write_current_kdl.return_value = write_kdl(nodes)
        self.app_state.saved_kdl = ""
        self.app_state.undo = MagicMock()
        self.app_state.undo.last_snapshot = None

    def get_nodes(self) -> list[KdlNode]:
        return self._nodes

    def push_undo(self, description: str, before: str, after: str):
        pass

    def mark_clean(self):
        pass

    def mark_dirty(self):
        pass


class TestInputPageAccelProfile(unittest.TestCase):
    def setUp(self):
        kdl = """input {
    touchpad {
        tap
        natural-scroll
    }
    mouse {
        natural-scroll
    }
}
"""
        self.nodes = parse_kdl(kdl)
        self.win = DummyWindow(self.nodes)
        self.page = InputPage(self.win)

    def test_accel_profiles_constant(self):
        self.assertEqual(ACCEL_PROFILES, ["default", "flat", "adaptive"])

    def test_touchpad_accel_profile_flat(self):
        self.page._set_tp("accel-profile", "flat")
        tp = find_or_create(self.nodes, "input", "touchpad")
        self.assertEqual(tp.child_arg("accel-profile"), "flat")
        out = write_kdl(self.nodes)
        self.assertIn('accel-profile "flat"', out)

    def test_touchpad_accel_profile_default_removes_child(self):
        # First set it to flat
        self.page._set_tp("accel-profile", "flat")
        tp = find_or_create(self.nodes, "input", "touchpad")
        self.assertEqual(tp.child_arg("accel-profile"), "flat")

        # Selecting default (index 0) removes the child node
        self.page._set_tp("accel-profile", ACCEL_PROFILES[0])
        self.assertIsNone(tp.get_child("accel-profile"))
        out = write_kdl(self.nodes)
        self.assertNotIn("accel-profile", out)

    def test_touchpad_accel_profile_none_removes_child(self):
        self.page._set_tp("accel-profile", "adaptive")
        tp = find_or_create(self.nodes, "input", "touchpad")
        self.assertEqual(tp.child_arg("accel-profile"), "adaptive")

        self.page._set_tp("accel-profile", None)
        self.assertIsNone(tp.get_child("accel-profile"))

    def test_mouse_accel_profile_adaptive(self):
        self.page._set_m("accel-profile", "adaptive")
        m = find_or_create(self.nodes, "input", "mouse")
        self.assertEqual(m.child_arg("accel-profile"), "adaptive")
        out = write_kdl(self.nodes)
        self.assertIn('accel-profile "adaptive"', out)

    def test_mouse_accel_profile_default_removes_child(self):
        # First set it to adaptive
        self.page._set_m("accel-profile", "adaptive")
        m = find_or_create(self.nodes, "input", "mouse")
        self.assertEqual(m.child_arg("accel-profile"), "adaptive")

        # Selecting default (index 0) removes the child node
        self.page._set_m("accel-profile", ACCEL_PROFILES[0])
        self.assertIsNone(m.get_child("accel-profile"))
        out = write_kdl(self.nodes)
        self.assertNotIn("accel-profile", out)

    def test_mouse_accel_profile_none_removes_child(self):
        self.page._set_m("accel-profile", "flat")
        m = find_or_create(self.nodes, "input", "mouse")
        self.assertEqual(m.child_arg("accel-profile"), "flat")

        self.page._set_m("accel-profile", None)
        self.assertIsNone(m.get_child("accel-profile"))

    def test_touchpad_flags(self):
        self.page._set_tp_flag("left-handed", True)
        self.page._set_tp_flag("middle-emulation", True)
        tp = find_or_create(self.nodes, "input", "touchpad")
        self.assertIsNotNone(tp.get_child("left-handed"))
        self.assertIsNotNone(tp.get_child("middle-emulation"))

        self.page._set_tp_flag("left-handed", False)
        self.assertIsNone(tp.get_child("left-handed"))

    def test_mouse_flags_and_scroll_options(self):
        self.page._set_m_flag("left-handed", True)
        self.page._set_m_flag("middle-emulation", True)
        self.page._set_m("scroll-method", "on-button-down")
        self.page._set_m("scroll-button", 274)
        self.page._set_m_flag("scroll-button-lock", True)

        m = find_or_create(self.nodes, "input", "mouse")
        self.assertIsNotNone(m.get_child("left-handed"))
        self.assertIsNotNone(m.get_child("middle-emulation"))
        self.assertEqual(m.child_arg("scroll-method"), "on-button-down")
        self.assertEqual(m.child_arg("scroll-button"), 274)
        self.assertIsNotNone(m.get_child("scroll-button-lock"))

        # Setting scroll-method back to default removes child
        self.page._set_m("scroll-method", "default")
        self.assertIsNone(m.get_child("scroll-method"))

    def test_general_input_flags(self):
        self.page._toggle_input_flag("workspace-auto-back-and-forth", True)
        inp = find_or_create(self.nodes, "input")
        self.assertIsNotNone(inp.get_child("workspace-auto-back-and-forth"))

        self.page._toggle_input_flag("workspace-auto-back-and-forth", False)
        self.assertIsNone(inp.get_child("workspace-auto-back-and-forth"))

    def test_trackpoint_settings(self):
        self.page._set_tr_flag("natural-scroll", True)
        self.page._set_tr_flag("left-handed", True)
        self.page._set_tr("accel-speed", 0.3)
        self.page._set_tr("accel-profile", "flat")

        tr = find_or_create(self.nodes, "input", "trackpoint")
        self.assertIsNotNone(tr.get_child("natural-scroll"))
        self.assertIsNotNone(tr.get_child("left-handed"))
        self.assertEqual(tr.child_arg("accel-speed"), 0.3)
        self.assertEqual(tr.child_arg("accel-profile"), "flat")

        # Trackpoint accel-profile "default" removes child
        self.page._set_tr("accel-profile", "default")
        self.assertIsNone(tr.get_child("accel-profile"))
