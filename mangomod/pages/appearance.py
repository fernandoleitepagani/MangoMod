"""Appearance page — border, shadow, blur (MangoWM)."""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, Gtk

from mangomod.pages.base import BasePage

def _parse_color(s: str) -> Gdk.RGBA:
    r = Gdk.RGBA()
    if s and not r.parse(s):
        r.parse("#7fc8ff")
    return r


def _rgba_to_hex(r: Gdk.RGBA) -> str:
    R, G, B, A = (int(c * 255) for c in (r.red, r.green, r.blue, r.alpha))
    return f"#{R:02x}{G:02x}{B:02x}" if A == 255 else f"#{R:02x}{G:02x}{B:02x}{A:02x}"


class AppearancePage(BasePage):
    def build(self):
        tb, _, _, content = self._make_toolbar_page("Appearance")
        self._content = content
        self._build_content()
        return tb

    def _get(self, key, default=None):
        return self._config.get(key, default)

    def _set(self, key, value):
        if value is None or value == "":
            self._config.remove(key)
        else:
            self._config.set(key, value)
        self._commit(f"appearance {key}")

    def _build_content(self):
        content = self._content

        # ── Border ──────────────────────────────────────────────────
        b = Adw.PreferencesGroup(title="Border")
        self._add_int(b, "borderpx", "Border Width (px)", 2)
        self._add_color(b, "focuscolor", "Focused Border Color", "#7fc8ff")
        self._add_color(b, "bordercolor", "Unfocused Border Color", "#3d3d3d")
        self._add_int(b, "border_radius", "Corner Radius (px)", 0)
        content.append(b)

        # ── Shadow ──────────────────────────────────────────────────
        s = Adw.PreferencesGroup(title="Shadow")
        self._add_bool(s, "shadows", "Enable Shadows", default=True)
        self._add_int(s, "shadows_size", "Shadow Size (px)", 12)
        self._add_int(s, "shadows_blur", "Shadow Blur", 12)
        self._add_int(s, "shadows_position_x", "Shadow Offset X", 0)
        self._add_int(s, "shadows_position_y", "Shadow Offset Y", 0)
        self._add_color(s, "shadowscolor", "Shadow Color", "#000000cc")
        self._add_bool(s, "shadow_only_floating", "Shadow Only on Floating Windows")
        content.append(s)

        # ── Blur ────────────────────────────────────────────────────
        bl = Adw.PreferencesGroup(title="Blur")
        self._add_bool(bl, "blur", "Enable Blur", default=True)
        self._add_bool(bl, "blur_layer", "Blur Layer Surfaces", default=True)
        self._add_bool(bl, "blur_optimized", "Optimized Blur", default=True)
        self._add_int(bl, "blur_params_num_passes", "Blur Passes", 3)
        self._add_int(bl, "blur_params_radius", "Blur Radius", 5)
        self._add_float(bl, "blur_params_noise", "Noise", 0.02)
        self._add_float(bl, "blur_params_brightness", "Brightness", 1.0)
        self._add_float(bl, "blur_params_contrast", "Contrast", 1.0)
        self._add_float(bl, "blur_params_saturation", "Saturation", 1.0)
        content.append(bl)

    # ── Row helpers ─────────────────────────────────────────────────

    def _add_bool(self, grp, key, title, default=False):
        cur = self._get(key)
        val = default
        if cur is not None:
            val = cur in ("1", "true", "yes")
        row = Adw.SwitchRow(title=title)
        row.set_active(val)
        row.connect(
            "notify::active",
            lambda r, k=key: self._set(k, 1 if r.get_active() else 0),
        )
        grp.add(row)

    def _add_int(self, grp, key, title, default):
        cur = self._get(key)
        try:
            val = int(cur) if cur is not None else default
        except ValueError:
            val = default
        adj = Gtk.Adjustment(value=val, lower=0, upper=200, step_increment=1)
        row = Adw.SpinRow(title=title, adjustment=adj, digits=0)
        row._last_val = val

        def _on(r, _, k=key):
            nv = int(r.get_value())
            if nv != getattr(r, "_last_val", None):
                r._last_val = nv
                self._set(k, nv)

        row.connect("notify::value", _on)
        grp.add(row)

    def _add_float(self, grp, key, title, default):
        cur = self._get(key)
        try:
            val = float(cur) if cur is not None else default
        except ValueError:
            val = default
        adj = Gtk.Adjustment(value=val, lower=0.0, upper=10.0, step_increment=0.05)
        row = Adw.SpinRow(title=title, adjustment=adj, digits=2)
        row._last_val = val

        def _on(r, _, k=key):
            nv = round(float(r.get_value()), 2)
            if abs(nv - getattr(r, "_last_val", 0.0)) > 0.001:
                r._last_val = nv
                self._set(k, nv)

        row.connect("notify::value", _on)
        grp.add(row)

    def _add_color(self, grp, key, title, default):
        cur = self._get(key) or default
        row = Adw.ActionRow(title=title)
        btn = Gtk.ColorDialogButton(
            dialog=Gtk.ColorDialog(title=title, with_alpha=True)
        )
        btn.set_rgba(_parse_color(cur))
        btn.set_valign(Gtk.Align.CENTER)
        btn.connect(
            "notify::rgba",
            lambda b, _, k=key: self._set(k, _rgba_to_hex(b.get_rgba())),
        )
        row.add_suffix(btn)
        grp.add(row)

    def refresh(self):
        for c in list(self._content):
            self._content.remove(c)
        self._build_content()
