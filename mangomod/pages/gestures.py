"""Gestures & Misc page — MangoWM misc behavior keys."""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk

from mangomod.pages.base import BasePage

class GesturesPage(BasePage):
    def build(self):
        tb, _, _, content = self._make_toolbar_page("Gestures & Misc")
        self._content = content
        self._build_content()
        return tb

    # ── config helpers ──────────────────────────────────────────────

    def _get(self, key, default=None):
        return self._config.get(key, default)

    def _set_bool(self, key, enabled):
        self._config.set(key, 1 if enabled else 0)
        self._commit(f"misc {key}")

    def _set_int(self, key, value):
        self._config.set(key, int(value))
        self._commit(f"misc {key}")

    # ── page ────────────────────────────────────────────────────────

    def _build_content(self):
        content = self._content

        # ── Hot Area ────────────────────────────────────────────────
        hot = Adw.PreferencesGroup(
            title="Hot Area",
            description="MangoWM supports a single hot area that opens the overview",
        )
        self._add_bool(hot, "enable_hotarea", "Enable Hot Area", default=True)
        self._add_int(
            hot, "hotarea_size", "Hot Area Size (px)", default=10,
            subtitle="Distance from the top-left corner that triggers the overview",
        )
        content.append(hot)

        # ── Focus & Cursor ──────────────────────────────────────────
        focus = Adw.PreferencesGroup(title="Focus & Cursor")
        self._add_bool(focus, "focus_on_activate", "Focus on Activate",
                       subtitle="Focus a window when an app requests activation",
                       default=True)
        self._add_bool(focus, "sloppyfocus", "Focus Follows Mouse", default=True)
        self._add_bool(focus, "warpcursor", "Warp Mouse to Focus", default=True)
        self._add_bool(focus, "focus_cross_monitor", "Allow Focus Cross Monitor",
                       default=False)
        self._add_bool(focus, "focus_cross_tag", "Allow Focus Cross Tag",
                       default=False)
        self._add_int(focus, "cursor_size", "Cursor Size (px)", default=24,
                      lo=8, hi=256)
        content.append(focus)

        # ── Tiling & Snapping ───────────────────────────────────────
        tiling = Adw.PreferencesGroup(title="Tiling & Snapping")
        self._add_bool(tiling, "enable_floating_snap", "Enable Floating Snap",
                       default=False)
        self._add_int(tiling, "snap_distance", "Snap Distance (px)", default=30,
                      lo=0, hi=500, step=2,
                      subtitle="Proximity at which floating windows snap to edges")
        self._add_bool(tiling, "drag_tile_to_tile", "Drag Tile to Tile",
                       default=True)
        self._add_bool(tiling, "drag_tile_small", "Drag Tile (Small)",
                       default=True)
        content.append(tiling)

        # ── Input Bindings ──────────────────────────────────────────
        bindings = Adw.PreferencesGroup(title="Input Bindings")
        self._add_int(
            bindings, "axis_bind_apply_timeout",
            "Axis Bind Apply Timeout (ms)", default=100,
            lo=0, hi=5000, step=10,
            subtitle="Delay before axis-based bindings are applied",
        )
        content.append(bindings)

        # ── Idle Inhibit ────────────────────────────────────────────
        idle = Adw.PreferencesGroup(
            title="Idle Inhibit",
            description="Control when apps may prevent the screen from idling",
        )
        self._add_bool(
            idle, "idle_inhibit_ignore_visible",
            "Ignore Visible Windows", default=False,
            subtitle="Only honour idle-inhibit requests from fullscreen apps",
        )
        self._add_bool(
            idle, "idle_inhibit_when_fullscreen",
            "Inhibit When Fullscreen", default=False,
            subtitle="Block idle when a fullscreen window is focused",
        )
        content.append(idle)

        # ── Compatibility ───────────────────────────────────────────
        compat = Adw.PreferencesGroup(title="Compatibility")
        self._add_bool(
            compat, "xwayland_persistence",
            "XWayland Persistence", default=True,
            subtitle="Keep the XWayland server alive even when no X clients are running",
        )
        self._add_bool(
            compat, "allow_shortcuts_inhibit",
            "Allow Shortcuts Inhibit", default=True,
            subtitle="Let apps (games, VMs) capture keyboard shortcuts",
        )
        content.append(compat)

    # ── row builders ────────────────────────────────────────────────

    def _add_bool(self, grp, key, title, subtitle=None, default=False):
        cur = self._get(key)
        if cur is None:
            val = default
        else:
            val = cur in ("1", "true", "yes")

        row = Adw.SwitchRow(title=title)
        if subtitle:
            row.set_subtitle(subtitle)
        row.set_active(val)

        def _on(r, _, k=key):
            self._set_bool(k, r.get_active())

        row.connect("notify::active", _on)
        grp.add(row)

    def _add_int(self, grp, key, title, default, lo=0, hi=10000,
                 step=1, subtitle=None):
        cur = self._get(key)
        try:
            val = int(cur) if cur is not None else default
        except (TypeError, ValueError):
            val = default

        adj = Gtk.Adjustment(value=val, lower=lo, upper=hi, step_increment=step)
        row = Adw.SpinRow(title=title, adjustment=adj, digits=0)
        if subtitle:
            row.set_subtitle(subtitle)
        row._last_val = val

        def _on(r, _, k=key):
            nv = int(r.get_value())
            if nv != getattr(r, "_last_val", None):
                r._last_val = nv
                self._set_int(k, nv)

        row.connect("notify::value", _on)
        grp.add(row)

    def refresh(self):
        for c in list(self._content):
            self._content.remove(c)
        self._build_content()
