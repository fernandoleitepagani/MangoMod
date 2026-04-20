"""Gestures & Miscellaneous settings page."""

from __future__ import annotations


import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk

from nirimod.kdl_parser import (
    KdlNode,
    find_or_create,
    set_node_flag,
    safe_switch_connect,
)
from nirimod.pages.base import BasePage, make_toolbar_page


class GesturesPage(BasePage):
    def build(self) -> Gtk.Widget:
        tb, _, _, content = self._make_toolbar_page("Gestures & Misc")
        self._content = content
        self._build_content()
        return tb

    def _build_content(self):
        content = self._content
        nodes = self._nodes

        hc_grp = Adw.PreferencesGroup(
            title="Hot Corners",
            description="Trigger actions when the cursor touches a screen corner",
        )
        gestures_node = find_or_create(nodes, "gestures")
        hc_node = gestures_node.get_child("hot-corners")
        hc_off = hc_node is not None and hc_node.get_child("off") is not None

        hc_row = Adw.SwitchRow(title="Enable Hot Corners")
        hc_row.set_active(not hc_off)
        safe_switch_connect(hc_row, not hc_off, self._set_hot_corners)
        hc_grp.add(hc_row)
        content.append(hc_grp)

        hko_grp = Adw.PreferencesGroup(title="Hotkey Overlay")
        hko_node = next((n for n in nodes if n.name == "hotkey-overlay"), None)

        skip_initial = (
            hko_node is not None and hko_node.get_child("skip-at-startup") is not None
        )
        skip_row = Adw.SwitchRow(
            title="Skip at Startup",
            subtitle="Don't show the hotkey overlay when niri starts",
        )
        skip_row.set_active(skip_initial)
        safe_switch_connect(skip_row, skip_initial, self._set_skip_hotkey_overlay)
        hko_grp.add(skip_row)
        content.append(hko_grp)

        ss_grp = Adw.PreferencesGroup(
            title="Screenshots", description="Path template for saved screenshots"
        )
        cur_path = next(
            (n.args[0] for n in nodes if n.name == "screenshot-path" and n.args),
            "~/Pictures/Screenshots/Screenshot from %Y-%m-%d %H-%M-%S.png",
        )
        path_row = Adw.EntryRow(title="Save Path (strftime format)")
        path_row.set_text(str(cur_path))
        path_row.set_show_apply_button(True)
        path_row.connect("apply", lambda r: self._set_screenshot_path(r.get_text()))
        ss_grp.add(path_row)
        content.append(ss_grp)

        ov_grp = Adw.PreferencesGroup(title="Overview")
        ov_node = find_or_create(nodes, "overview")
        ws_shadow_node = ov_node.get_child("workspace-shadow")

        ws_shadow_initial = (
            ws_shadow_node is None or ws_shadow_node.get_child("off") is None
        )
        ws_shadow_row = Adw.SwitchRow(
            title="Workspace Shadow in Overview",
            subtitle="Show drop shadows under workspaces in overview mode",
        )
        ws_shadow_row.set_active(ws_shadow_initial)
        safe_switch_connect(
            ws_shadow_row, ws_shadow_initial, self._set_overview_ws_shadow
        )
        ov_grp.add(ws_shadow_row)
        content.append(ov_grp)

    def _set_hot_corners(self, enabled: bool):
        gestures = find_or_create(self._nodes, "gestures")
        hc = gestures.get_child("hot-corners")
        if hc is None:
            hc = KdlNode("hot-corners")
            gestures.children.append(hc)
        set_node_flag(hc, "off", not enabled)
        self._commit("gestures hot-corners")

    def _set_skip_hotkey_overlay(self, skip: bool):
        nodes = self._nodes
        hko = next((n for n in nodes if n.name == "hotkey-overlay"), None)
        if hko is None:
            hko = KdlNode("hotkey-overlay")
            nodes.append(hko)
        set_node_flag(hko, "skip-at-startup", skip)
        self._commit("hotkey-overlay skip-at-startup")

    def _set_screenshot_path(self, path: str):
        nodes = self._nodes
        existing = next((n for n in nodes if n.name == "screenshot-path"), None)
        if path.strip():
            if existing:
                existing.args = [path.strip()]
            else:
                nodes.append(KdlNode("screenshot-path", args=[path.strip()]))
        elif existing:
            nodes.remove(existing)
        self._commit("screenshot-path")

    def _set_overview_ws_shadow(self, enabled: bool):
        ov = find_or_create(self._nodes, "overview")
        ws_shadow = ov.get_child("workspace-shadow")
        if ws_shadow is None:
            ws_shadow = KdlNode("workspace-shadow")
            ov.children.append(ws_shadow)
        set_node_flag(ws_shadow, "off", not enabled)
        self._commit("overview workspace-shadow")

    def refresh(self):
        for child in list(self._content):
            self._content.remove(child)
        self._build_content()
