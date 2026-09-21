"""Animations page — MangoWM flat keys."""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk

from mangomod.pages.base import BasePage

ANIMATION_TYPES = ["none", "slide", "zoom", "fade"]


class AnimationsPage(BasePage):
    def __init__(self, window):
        super().__init__(window)

    def build(self):
        tb, _, _, content = self._make_toolbar_page("Animations")
        self._content = content
        self._build_content()
        return tb

    # --- helpers ---

    def _get(self, key, default=None):
        return self._config.get(key, default)

    def _set(self, key, value):
        if value is None or value == "":
            self._config.remove(key)
        else:
            self._config.set(key, value)
        self._commit(f"animations {key}")

    # --- page ---

    def _build_content(self):
        content = self._content

        # Enable Animations
        en = Adw.PreferencesGroup(title="Animations")
        row = Adw.SwitchRow(title="Enable Animations", subtitle="Master switch")
        row.set_active(self._get("animations", "1") not in ("0", "false"))
        row.connect("notify::active", lambda r, _: self._set("animations", 1 if r.get_active() else 0))
        en.add(row)
        content.append(en)

        # Window Open
        open_grp = Adw.PreferencesGroup(title="Window Open")
        self._add_choice(open_grp, "animation_type_open", "Animation Type", ANIMATION_TYPES)
        self._add_bool(open_grp, "animation_fade_in", "Enable Fade-In", default=True)
        self._add_int(open_grp, "animation_duration_open", "Duration (ms)", 400)
        self._add_str(open_grp, "animation_curve_open", "Curve (x1,y1,x2,y2)", "0.46,1.0,0.29,1")
        self._add_str(open_grp, "animation_curve_opafadein", "Fade-In Opacity Curve", "0.46,1.0,0.29,1")
        self._add_float(open_grp, "zoom_initial_ratio", "Zoom Initial Ratio", 0.3)
        self._add_float(open_grp, "zoom_end_ratio", "Zoom End Ratio", 0.8)
        self._add_float(open_grp, "fadein_begin_opacity", "Fade-In Begin Opacity", 0.5)
        content.append(open_grp)

        # Window Close
        close_grp = Adw.PreferencesGroup(title="Window Close")
        self._add_choice(close_grp, "animation_type_close", "Animation Type", ANIMATION_TYPES)
        self._add_bool(close_grp, "animation_fade_out", "Enable Fade-Out", default=True)
        self._add_int(close_grp, "animation_duration_close", "Duration (ms)", 800)
        self._add_str(close_grp, "animation_curve_close", "Curve (x1,y1,x2,y2)", "0.08,0.92,0,1")
        self._add_str(close_grp, "animation_curve_opafadeout", "Fade-Out Opacity Curve", "0.5,0.5,0.5,0.5")
        self._add_float(close_grp, "fadeout_begin_opacity", "Fade-Out Begin Opacity", 0.8)
        content.append(close_grp)

        # Move & Resize
        move_grp = Adw.PreferencesGroup(title="Window Move &amp; Resize")
        self._add_int(move_grp, "animation_duration_move", "Duration (ms)", 500)
        self._add_str(move_grp, "animation_curve_move", "Curve (x1,y1,x2,y2)", "0.46,1.0,0.29,1")
        content.append(move_grp)

        # Tag switch
        tag_grp = Adw.PreferencesGroup(title="Tag / Workspace Switch")
        self._add_int(tag_grp, "animation_duration_tag", "Duration (ms)", 350)
        self._add_str(tag_grp, "animation_curve_tag", "Curve (x1,y1,x2,y2)", "0.46,1.0,0.29,1")
        self._add_int_choice(tag_grp, "tag_animation_direction", "Direction", [("Horizontal", 1), ("Vertical", 0)])
        content.append(tag_grp)

        # Focus
        focus_grp = Adw.PreferencesGroup(title="Focus")
        self._add_int(focus_grp, "animation_duration_focus", "Duration (ms)", 0)
        self._add_str(focus_grp, "animation_curve_focus", "Curve (x1,y1,x2,y2)", "0.46,1.0,0.29,1")
        content.append(focus_grp)

        # Layer animations
        layer = Adw.PreferencesGroup(title="Layer Animations")
        self._add_bool(layer, "layer_animations", "Enable Layer Animations", default=True)
        self._add_choice(layer, "layer_animation_type_open", "Layer Open Type", ANIMATION_TYPES)
        self._add_choice(layer, "layer_animation_type_close", "Layer Close Type", ANIMATION_TYPES)
        content.append(layer)

    # --- row builders ---

    def _add_choice(self, grp, key, title, choices):
        cur = self._get(key)
        model = Gtk.StringList.new(choices)
        row = Adw.ComboRow(title=title, model=model)
        row.set_selected(choices.index(cur) if cur in choices else choices.index("none"))
        row.connect("notify::selected", lambda r, _, k=key, c=choices: self._set(k, c[r.get_selected()]))
        grp.add(row)

    def _add_int_choice(self, grp, key, title, choices):
        cur = self._get(key)
        try:
            cur_i = int(cur) if cur is not None else None
        except ValueError:
            cur_i = None
        labels = [l for l, _ in choices]
        values = [v for _, v in choices]
        model = Gtk.StringList.new(labels)
        row = Adw.ComboRow(title=title, model=model)
        row.set_selected(values.index(cur_i) if cur_i in values else 0)
        row.connect("notify::selected", lambda r, _, k=key, v=values: self._set(k, v[r.get_selected()]))
        grp.add(row)

    def _add_bool(self, grp, key, title, default=False):
        cur = self._get(key)
        val = 1 if default else 0
        if cur is not None:
            try:
                val = int(cur)
            except ValueError:
                val = 1 if cur.lower() in ("true", "yes") else 0
        row = Adw.SwitchRow(title=title)
        row.set_active(bool(val))
        row.connect("notify::active", lambda r, k=key: self._set(k, 1 if r.get_active() else 0))
        grp.add(row)

    def _add_int(self, grp, key, title, default):
        cur = self._get(key)
        try:
            val = int(cur) if cur is not None else default
        except ValueError:
            val = default
        adj = Gtk.Adjustment(value=val, lower=0, upper=5000, step_increment=10)
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
        adj = Gtk.Adjustment(value=val, lower=0.0, upper=3.0, step_increment=0.05)
        row = Adw.SpinRow(title=title, adjustment=adj, digits=2)
        row._last_val = val

        def _on(r, _, k=key):
            nv = round(float(r.get_value()), 2)
            if abs(nv - getattr(r, "_last_val", 0.0)) > 0.001:
                r._last_val = nv
                self._set(k, nv)

        row.connect("notify::value", _on)
        grp.add(row)

    def _add_str(self, grp, key, title, placeholder=""):
        cur = self._get(key)
        row = Adw.EntryRow(title=title)
        if cur is not None:
            row.set_text(str(cur))
        row.set_show_apply_button(True)
        if placeholder:
            row.set_tooltip_text(f"e.g. {placeholder}")
        row.connect("apply", lambda r, k=key: self._set(k, r.get_text().strip()))
        grp.add(row)

    def refresh(self):
        for c in list(self._content):
            self._content.remove(c)
        self._build_content()
