"""Input page — MangoWM flat keys."""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk

from mangomod.pages.base import BasePage

class InputPage(BasePage):
    def build(self):
        tb, _, _, content = self._make_toolbar_page("Input")
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
        self._commit(f"input {key}")

    def _build_content(self):
        content = self._content

        # ── Keyboard ────────────────────────────────────────────────
        kb = Adw.PreferencesGroup(title="Keyboard")
        self._add_str(kb, "xkb_rules_layout", "Layout", "us,ru")
        self._add_str(kb, "xkb_rules_variant", "Variant", "dvorak")
        self._add_str(kb, "xkb_rules_options", "Options", "grp:win_space_toggle")
        self._add_int(kb, "repeat_rate", "Repeat Rate (keys/sec)", 25,
                      lo=1, hi=200)
        self._add_int(kb, "repeat_delay", "Repeat Delay (ms)", 600,
                      lo=100, hi=3000, step=10)
        self._add_bool(kb, "numlockon", "Enable Num Lock on Startup")
        content.append(kb)

        # ── Touchpad ────────────────────────────────────────────────
        tp = Adw.PreferencesGroup(title="Touchpad")
        self._add_bool(tp, "tap_to_click", "Tap to Click", default=True)
        self._add_bool(tp, "tap_and_drag", "Tap and Drag", default=True)
        self._add_bool(tp, "drag_lock", "Drag Lock")
        self._add_bool(tp, "natural_scrolling", "Natural Scroll")
        self._add_bool(tp, "disable_while_typing", "Disable While Typing", default=True)
        self._add_bool(tp, "left_handed", "Left Handed")
        self._add_bool(tp, "middle_button_emulation", "Middle Click Emulation")
        self._add_float(tp, "swipe_min_threshold", "Swipe Threshold", 40.0,
                        lo=0.0, hi=500.0, step=5.0)
        content.append(tp)

        # ── Mouse ───────────────────────────────────────────────────
        m = Adw.PreferencesGroup(title="Mouse")
        self._add_bool(m, "natural_scrolling_mouse", "Natural Scroll")
        self._add_bool(m, "left_handed_mouse", "Left Handed")
        content.append(m)

    # ── row builders ────────────────────────────────────────────────

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

    def _add_int(self, grp, key, title, default, lo=0, hi=10000, step=1):
        cur = self._get(key)
        try:
            val = int(cur) if cur is not None else default
        except (TypeError, ValueError):
            val = default
        adj = Gtk.Adjustment(value=val, lower=lo, upper=hi, step_increment=step)
        row = Adw.SpinRow(title=title, adjustment=adj, digits=0)
        row._last_val = val

        def _on(r, _, k=key):
            nv = int(r.get_value())
            if nv != getattr(r, "_last_val", None):
                r._last_val = nv
                self._set(k, nv)

        row.connect("notify::value", _on)
        grp.add(row)

    def _add_float(self, grp, key, title, default, lo=0.0, hi=1000.0, step=1.0):
        cur = self._get(key)
        try:
            val = float(cur) if cur is not None else default
        except (TypeError, ValueError):
            val = default
        adj = Gtk.Adjustment(value=val, lower=lo, upper=hi, step_increment=step)
        row = Adw.SpinRow(title=title, adjustment=adj, digits=1)
        row._last_val = val

        def _on(r, _, k=key):
            nv = round(float(r.get_value()), 1)
            if abs(nv - getattr(r, "_last_val", 0.0)) > 0.01:
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
