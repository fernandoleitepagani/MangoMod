"""Appearance page — borders, focus ring, shadows, corner radius."""

from __future__ import annotations


import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, Gtk

from nirimod.kdl_parser import KdlNode, find_or_create, set_child_arg, set_node_flag
from nirimod.pages.base import BasePage, make_toolbar_page


def _parse_color(color_str: str) -> Gdk.RGBA:
    rgba = Gdk.RGBA()
    if color_str and not rgba.parse(color_str):
        rgba.parse("#7fc8ff")
    return rgba


class AppearancePage(BasePage):
    def build(self) -> Gtk.Widget:
        tb, _, _, content = make_toolbar_page("Appearance")
        self._content = content
        self._build_content()
        return tb

    def _build_content(self):
        content = self._content
        nodes = self._nodes
        layout = find_or_create(nodes, "layout")

        fr_node = layout.get_child("focus-ring") or KdlNode("focus-ring")
        fr_group = self._build_border_group("Focus Ring", "focus-ring", fr_node, layout)
        content.append(fr_group)

        b_node = layout.get_child("border") or KdlNode("border")
        b_group = self._build_border_group("Border", "border", b_node, layout)
        content.append(b_group)

        shadow_grp = Adw.PreferencesGroup(title="Shadow")
        shadow_node = layout.get_child("shadow") or KdlNode("shadow")

        shadow_on_row = Adw.SwitchRow(title="Enable Shadows")
        shadow_on_row.set_active(shadow_node.get_child("on") is not None)
        shadow_on_row.connect(
            "notify::active", lambda r, _: self._set_shadow_flag("on", r.get_active())
        )
        shadow_grp.add(shadow_on_row)

        soft_val = int(shadow_node.child_arg("softness") or 30)
        softness_adj = Gtk.Adjustment(
            value=soft_val, lower=0, upper=100, step_increment=1
        )
        softness_row = Adw.SpinRow(
            title="Softness (blur radius)", adjustment=softness_adj, digits=0
        )

        softness_row._last_val = soft_val

        def _on_soft_changed(r, _):
            new_val = int(r.get_value())
            if new_val != getattr(r, "_last_val", None):
                r._last_val = new_val
                self._set_shadow("softness", new_val)

        softness_row.connect("notify::value", _on_soft_changed)
        shadow_grp.add(softness_row)

        spread_val = int(shadow_node.child_arg("spread") or 5)
        spread_adj = Gtk.Adjustment(
            value=spread_val, lower=-50, upper=100, step_increment=1
        )
        spread_row = Adw.SpinRow(title="Spread", adjustment=spread_adj, digits=0)

        spread_row._last_val = spread_val

        def _on_spread_changed(r, _):
            new_val = int(r.get_value())
            if new_val != getattr(r, "_last_val", None):
                r._last_val = new_val
                self._set_shadow("spread", new_val)

        spread_row.connect("notify::value", _on_spread_changed)
        shadow_grp.add(spread_row)

        color_str = shadow_node.child_arg("color") or "#0007"
        color_row = Adw.ActionRow(title="Shadow Color")
        color_btn = Gtk.ColorDialogButton(
            dialog=Gtk.ColorDialog(title="Shadow Color", with_alpha=True)
        )
        color_btn.set_rgba(_parse_color(color_str))
        color_btn.set_valign(Gtk.Align.CENTER)
        color_btn.connect(
            "notify::rgba", lambda b, _: self._set_shadow_color(b.get_rgba())
        )
        color_row.add_suffix(color_btn)
        shadow_grp.add(color_row)

        draw_behind_row = Adw.SwitchRow(
            title="Draw Behind Window",
            subtitle="Fixes corner artifacts with non-CSD apps",
        )
        draw_behind_row.set_active(
            shadow_node.get_child("draw-behind-window") is not None
        )
        draw_behind_row.connect(
            "notify::active",
            lambda r, _: self._set_shadow_flag("draw-behind-window", r.get_active()),
        )
        shadow_grp.add(draw_behind_row)
        content.append(shadow_grp)

        misc_grp = Adw.PreferencesGroup(title="Window Geometry")

        # geometry-corner-radius is a window-rule-level setting but also applied globally
        # get current cr if it exists
        wr_nodes = [
            n
            for n in nodes
            if n.name == "window-rule"
            and not n.get_children("match")
            and n.get_child("geometry-corner-radius")
        ]
        cr_val = int(wr_nodes[0].child_arg("geometry-corner-radius") if wr_nodes else 0)
        cr_adj = Gtk.Adjustment(value=cr_val, lower=0, upper=40, step_increment=1)
        cr_row = Adw.SpinRow(
            title="Corner Radius (px, applied via window-rule)",
            adjustment=cr_adj,
            digits=0,
        )

        cr_row._last_val = cr_val

        def _on_cr_changed(r, _):
            new_val = int(r.get_value())
            if new_val != getattr(r, "_last_val", None):
                r._last_val = new_val
                self._set_corner_radius(new_val)

        cr_row.connect("notify::value", _on_cr_changed)
        misc_grp.add(cr_row)
        content.append(misc_grp)

    def _build_border_group(
        self, title: str, key: str, node: KdlNode, layout: KdlNode
    ) -> Adw.PreferencesGroup:
        grp = Adw.PreferencesGroup(title=title)

        off_row = Adw.SwitchRow(title="Enable")
        off_row.set_active(node.get_child("off") is None)
        off_row.connect(
            "notify::active",
            lambda r, _, k=key: self._set_layout_border_flag(
                k, "off", not r.get_active()
            ),
        )
        grp.add(off_row)

        width_val = int(node.child_arg("width") or 4)
        width_adj = Gtk.Adjustment(value=width_val, lower=1, upper=20, step_increment=1)
        width_row = Adw.SpinRow(title="Width (px)", adjustment=width_adj, digits=0)

        width_row._last_val = width_val

        def _on_width_changed(r, _, k=key):
            new_val = int(r.get_value())
            if new_val != getattr(r, "_last_val", None):
                r._last_val = new_val
                self._set_layout_border(k, "width", new_val)

        width_row.connect("notify::value", _on_width_changed)
        grp.add(width_row)

        for color_key, color_label in [
            ("active-color", "Active Color"),
            ("inactive-color", "Inactive Color"),
        ]:
            c_str = node.child_arg(color_key) or (
                "#7fc8ff" if "active" in color_key else "#202020"
            )
            c_row = Adw.ActionRow(title=color_label)
            c_btn = Gtk.ColorDialogButton(
                dialog=Gtk.ColorDialog(title=color_label, with_alpha=True)
            )
            c_btn.set_rgba(_parse_color(c_str))
            c_btn.set_valign(Gtk.Align.CENTER)
            c_btn.connect(
                "notify::rgba",
                lambda b, _, k=key, ck=color_key: self._set_layout_border(
                    k, ck, self._rgba_to_hex(b.get_rgba())
                ),
            )
            c_row.add_suffix(c_btn)
            grp.add(c_row)

        return grp

    @staticmethod
    def _rgba_to_hex(rgba: Gdk.RGBA) -> str:
        r = int(rgba.red * 255)
        g = int(rgba.green * 255)
        b = int(rgba.blue * 255)
        a = int(rgba.alpha * 255)
        if a == 255:
            return f"#{r:02x}{g:02x}{b:02x}"
        return f"#{r:02x}{g:02x}{b:02x}{a:02x}"

    def _get_layout(self):
        return find_or_create(self._nodes, "layout")

    def _get_border_node(self, key: str) -> KdlNode:
        layout = self._get_layout()
        node = layout.get_child(key)
        if node is None:
            node = KdlNode(key)
            layout.children.append(node)
        return node

    def _set_layout_border(self, bkey: str, prop: str, value):
        node = self._get_border_node(bkey)
        set_child_arg(node, prop, value)
        self._commit(f"{bkey} {prop}")

    def _set_layout_border_flag(self, bkey: str, flag: str, enabled: bool):
        node = self._get_border_node(bkey)
        set_node_flag(node, flag, enabled)
        self._commit(f"{bkey} {flag}")

    def _get_shadow_node(self) -> KdlNode:
        layout = self._get_layout()
        node = layout.get_child("shadow")
        if node is None:
            node = KdlNode("shadow")
            layout.children.append(node)
        return node

    def _set_shadow(self, prop: str, value):
        set_child_arg(self._get_shadow_node(), prop, value)
        self._commit(f"shadow {prop}")

    def _set_shadow_flag(self, flag: str, enabled: bool):
        set_node_flag(self._get_shadow_node(), flag, enabled)
        self._commit(f"shadow {flag}")

    def _set_shadow_color(self, rgba: Gdk.RGBA):
        set_child_arg(self._get_shadow_node(), "color", self._rgba_to_hex(rgba))
        self._commit("shadow color")

    def _set_corner_radius(self, radius: int):
        # Apply via global window-rule
        nodes = self._nodes

        wr = next(
            (
                n
                for n in nodes
                if n.name == "window-rule"
                and n.get_child("geometry-corner-radius")
                and not n.get_children("match")
            ),
            None,
        )
        if radius > 0:
            if wr is None:
                wr = KdlNode("window-rule")
                nodes.append(wr)
            set_child_arg(wr, "geometry-corner-radius", radius)
            set_child_arg(wr, "clip-to-geometry", True)
        elif wr is not None:
            nodes.remove(wr)
        self._commit("corner radius")

    def refresh(self):
        for child in list(self._content):
            self._content.remove(child)
        self._build_content()
