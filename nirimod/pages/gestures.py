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

_CORNERS = [
    ("top-left",     "Top-Left",     "Moves cursor to the top-left corner"),
    ("top-right",    "Top-Right",    "Moves cursor to the top-right corner"),
    ("bottom-left",  "Bottom-Left",  "Moves cursor to the bottom-left corner"),
    ("bottom-right", "Bottom-Right", "Moves cursor to the bottom-right corner"),
]


class GesturesPage(BasePage):
    def build(self) -> Gtk.Widget:
        tb, _, _, content = self._make_toolbar_page("Gestures & Misc")
        self._content = content
        self._build_content()
        return tb

    def _build_content(self):
        content = self._content
        nodes = self._nodes

        # ── Hot Corners ───────────────────────────────────────────────────────
        hc_grp = Adw.PreferencesGroup(
            title="Hot Corners",
            description="Trigger the overview when the cursor touches a screen corner (niri ≥ 25.05)",
        )
        gestures_node = next((n for n in nodes if n.name == "gestures"), None)
        hc_node = gestures_node.get_child("hot-corners") if gestures_node else None
        hc_off = hc_node is not None and hc_node.get_child("off") is not None
        hc_enabled = not hc_off

        # Which individual corners are active
        active_corners: set[str] = set()
        if hc_node and not hc_off:
            for corner_key, _, _ in _CORNERS:
                if hc_node.get_child(corner_key) is not None:
                    active_corners.add(corner_key)

        # ExpanderRow = the enable/disable switch + collapsible corner list
        hc_expander = Adw.ExpanderRow(
            title="Enable Hot Corners",
            subtitle="Expand to choose which corners are active (default: top-left)",
        )
        hc_expander.set_expanded(hc_enabled)
        hc_expander.set_show_enable_switch(True)
        hc_expander.set_enable_expansion(hc_enabled)

        # Per-corner rows nested inside the expander
        corner_rows: dict[str, Adw.SwitchRow] = {}
        for corner_key, corner_label, corner_subtitle in _CORNERS:
            sr = Adw.SwitchRow(title=corner_label, subtitle=corner_subtitle)
            is_active = corner_key in active_corners
            sr.set_active(is_active)
            safe_switch_connect(
                sr, is_active,
                lambda enabled, k=corner_key: self._set_corner(k, enabled),
            )
            hc_expander.add_row(sr)
            corner_rows[corner_key] = sr

        # Wire the expander's enable-switch to the hot corners on/off mutation
        hc_expander._last_enabled = hc_enabled

        def _on_expander_toggled(expander, _param):
            val = expander.get_enable_expansion()
            if val != getattr(expander, "_last_enabled", None):
                expander._last_enabled = val
                self._set_hot_corners(val)

        hc_expander.connect("notify::enable-expansion", _on_expander_toggled)

        hc_grp.add(hc_expander)
        content.append(hc_grp)


        # ── Hotkey Overlay ────────────────────────────────────────────────────
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

        # ── Screenshots ───────────────────────────────────────────────────────
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

        # ── Overview ──────────────────────────────────────────────────────────
        ov_grp = Adw.PreferencesGroup(title="Overview")
        ov_node = next((n for n in nodes if n.name == "overview"), None)
        ws_shadow_node = ov_node.get_child("workspace-shadow") if ov_node else None

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

    # ── Mutation methods ──────────────────────────────────────────────────────

    def _get_hot_corners_node(self) -> KdlNode:
        gestures = find_or_create(self._nodes, "gestures")
        hc = gestures.get_child("hot-corners")
        if hc is None:
            hc = KdlNode("hot-corners")
            hc.leading_trivia = "\n"
            gestures.children.append(hc)
        return hc

    def _set_hot_corners(self, enabled: bool):
        hc = self._get_hot_corners_node()
        set_node_flag(hc, "off", not enabled)
        self._commit("gestures hot-corners")

    def _set_corner(self, corner_key: str, enabled: bool):
        """Enable or disable an individual hot corner (niri ≥ 25.11)."""
        hc = self._get_hot_corners_node()
        # Remove 'off' if it exists — enabling a corner implicitly enables hot corners
        set_node_flag(hc, "off", False)
        set_node_flag(hc, corner_key, enabled)
        self._commit(f"hot-corner {corner_key}")

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
