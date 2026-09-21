"""Outputs / Monitors page — interactive canvas (MangoWM monitorrule)."""

from __future__ import annotations

import json
import math
import os
import subprocess

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk, GLib

from mangomod.mango_config import parse_kv_rule, build_kv_rule
from mangomod.pages.base import BasePage


SNAP_THRESHOLD = 30
ROTATION_LABELS = ["Normal", "90°", "180°", "270°"]
ROTATION_VALUES = [0, 1, 2, 3]


def _normalize_monitor_name(name: str) -> str:
    """Strip common regex anchors so '^eDP-1$' and 'eDP-1' compare equal."""
    return name.strip().lstrip("^").rstrip("$").strip()


def _snap_axis_origin(other_edge, dragged_size, dragged_at_start, other_at_start):
    if dragged_at_start:
        if other_at_start:
            return round(other_edge)
        return math.ceil(other_edge)
    origin = other_edge - dragged_size
    if other_at_start:
        return math.floor(origin)
    return round(origin)


# ── runtime queries ────────────────────────────────────────────────────

def _query_wlr_randr() -> list[dict] | None:
    try:
        r = subprocess.run(
            ["wlr-randr", "--json"],
            capture_output=True, text=True, timeout=3,
        )
        if r.returncode != 0:
            return None
        data = json.loads(r.stdout)
        if isinstance(data, dict):
            out = []
            for name, info in data.items():
                info = dict(info)
                info["name"] = name
                out.append(info)
            return out
        if isinstance(data, list):
            return data
        return None
    except (FileNotFoundError, subprocess.SubprocessError, json.JSONDecodeError):
        return None


def _list_connected_outputs() -> list[str]:
    names: list[str] = []
    try:
        for entry in sorted(os.listdir("/sys/class/drm")):
            if not entry.startswith("card") or "-" not in entry:
                continue
            _, _, out = entry.partition("-")
            if not out:
                continue
            try:
                with open(f"/sys/class/drm/{entry}/status") as fh:
                    if fh.read().strip() == "connected":
                        names.append(out)
            except OSError:
                continue
    except OSError:
        pass
    return names


# ── monitor model ──────────────────────────────────────────────────────

class Monitor:
    def __init__(
        self,
        name: str,
        width: int = 1920,
        height: int = 1080,
        scale: float = 1.0,
        x: int = 0,
        y: int = 0,
        rr: int = 0,
        vrr: bool = False,
        disabled: bool = False,
        modes: list[dict] | None = None,
    ):
        self.name = name
        self.width = width
        self.height = height
        self.scale = scale
        self.x = x
        self.y = y
        self.rr = rr
        self.vrr = vrr
        self.disabled = disabled
        self.modes = modes or [{"width": width, "height": height, "refresh": 60.0}]

    def logical_w(self) -> float:
        w, h = (
            (self.height, self.width) if self.rr in (1, 3) else (self.width, self.height)
        )
        return w / self.scale

    def logical_h(self) -> float:
        w, h = (
            (self.height, self.width) if self.rr in (1, 3) else (self.width, self.height)
        )
        return h / self.scale

    def to_rule(self) -> str:
        parts: dict[str, str] = {"name": self.name}
        parts["width"] = str(self.width)
        parts["height"] = str(self.height)
        parts["x"] = str(int(round(self.x)))
        parts["y"] = str(int(round(self.y)))
        parts["scale"] = str(self.scale)
        if self.rr:
            parts["rr"] = str(self.rr)
        if self.vrr:
            parts["vrr"] = "1"
        if self.disabled:
            parts["disabled"] = "1"
        return build_kv_rule(parts)


class _Canvas(Gtk.DrawingArea):
    def __init__(self):
        super().__init__()
        self.set_hexpand(True)
        self.set_content_height(360)


# ── page ───────────────────────────────────────────────────────────────

class OutputsPage(BasePage):
    def __init__(self, window):
        super().__init__(window)
        self._monitors: list[Monitor] = []
        self._selected: str | None = None
        self._detail_box: Gtk.Box | None = None
        self._out_combo: Adw.ComboRow | None = None

        self._drag_name: str | None = None
        self._drag_start_scale: float = 1.0
        self._drag_start_offset: tuple[float, float] = (0.0, 0.0)
        self._drag_current_lx: float = 0.0
        self._drag_current_ly: float = 0.0
        self._last_dx: float = 0.0
        self._last_dy: float = 0.0

        self._canvas_scale: float = 1.0
        self._canvas_offset: tuple[float, float] = (0.0, 0.0)
        self._draw_ready: bool = False

    def build(self):
        tb, header, _, content = self._make_toolbar_page("Outputs")
        self._content = content

        add_fake = Gtk.Button(icon_name="list-add-symbolic")
        add_fake.set_tooltip_text("Add fake monitor for testing")
        add_fake.add_css_class("flat")
        add_fake.connect("clicked", lambda *_: self._add_fake_monitor())
        header.pack_end(add_fake)

        refresh_btn = Gtk.Button(icon_name="view-refresh-symbolic")
        refresh_btn.set_tooltip_text("Reload monitors")
        refresh_btn.add_css_class("flat")
        refresh_btn.connect("clicked", lambda *_: self.refresh())
        header.pack_end(refresh_btn)

        frame = Gtk.Frame()
        frame.add_css_class("card")
        frame.set_margin_bottom(8)
        self._canvas = _Canvas()
        self._canvas.set_draw_func(self._draw_canvas)
        frame.set_child(self._canvas)
        content.append(frame)

        drag = Gtk.GestureDrag()
        drag.connect("drag-begin", self._on_drag_begin)
        drag.connect("drag-update", self._on_drag_update)
        drag.connect("drag-end", self._on_drag_end)
        self._canvas.add_controller(drag)

        click = Gtk.GestureClick()
        click.connect("pressed", self._on_canvas_click)
        self._canvas.add_controller(click)

        self._out_combo = Adw.ComboRow(title="Monitor")
        self._out_combo.connect("notify::selected", self._on_output_selected)
        sel_grp = Adw.PreferencesGroup()
        sel_grp.add(self._out_combo)
        content.append(sel_grp)

        self._detail_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        content.append(self._detail_box)

        self.refresh()
        return tb

    # ── loading ─────────────────────────────────────────────────────

    def refresh(self):
        self._monitors = self._load_monitors()
        self._update_combo()
        if self._monitors:
            if not (self._selected and any(m.name == self._selected for m in self._monitors)):
                self._selected = self._monitors[0].name
            self._load_detail()
        if self._canvas:
            self._canvas.queue_draw()

    def _load_monitors(self) -> list[Monitor]:
        runtime: dict[str, dict] = {}
        rr_data = _query_wlr_randr()
        if rr_data:
            for entry in rr_data:
                name = entry.get("name")
                if not name:
                    continue
                modes = []
                cur_mode = None
                for m in entry.get("modes", []):
                    mode = {
                        "width": int(m.get("width", 1920)),
                        "height": int(m.get("height", 1080)),
                        "refresh": float(m.get("refresh", 60.0)),
                    }
                    modes.append(mode)
                    if m.get("current"):
                        cur_mode = mode
                if cur_mode is None and modes:
                    cur_mode = modes[0]
                pos = entry.get("position") or {}
                runtime[name] = {
                    "width": (cur_mode or {}).get("width", 1920),
                    "height": (cur_mode or {}).get("height", 1080),
                    "modes": modes or [{"width": 1920, "height": 1080, "refresh": 60.0}],
                    "x": int(pos.get("x", 0)),
                    "y": int(pos.get("y", 0)),
                    "scale": float(entry.get("scale", 1.0)),
                    "transform": entry.get("transform", "normal"),
                }

        config_rules: dict[str, dict[str, str]] = {}
        for rule in self._config.get_all("monitorrule"):
            p = parse_kv_rule(rule)
            if "name" in p:
                key = _normalize_monitor_name(p["name"])
                config_rules[key] = p

        seen: set[str] = set()
        result: list[Monitor] = []

        for name, rt in runtime.items():
            seen.add(name)
            cfg = config_rules.get(name, {})
            try:
                width = int(cfg.get("width", rt["width"]))
                height = int(cfg.get("height", rt["height"]))
                scale = float(cfg.get("scale", rt["scale"]))
                x = int(cfg.get("x", rt["x"]))
                y = int(cfg.get("y", rt["y"]))
                rr = int(cfg.get("rr", 0))
            except (TypeError, ValueError):
                continue
            vrr = cfg.get("vrr", "0") in ("1", "true")
            disabled = cfg.get("disabled", "0") in ("1", "true")
            result.append(Monitor(
                name=name, width=width, height=height, scale=scale,
                x=x, y=y, rr=rr, vrr=vrr, disabled=disabled, modes=rt["modes"],
            ))

        for name, cfg in config_rules.items():
            if name in seen:
                continue
            try:
                result.append(Monitor(
                    name=name,
                    width=int(cfg.get("width", 1920)),
                    height=int(cfg.get("height", 1080)),
                    scale=float(cfg.get("scale", 1.0)),
                    x=int(cfg.get("x", 0)),
                    y=int(cfg.get("y", 0)),
                    rr=int(cfg.get("rr", 0)),
                    vrr=cfg.get("vrr", "0") in ("1", "true"),
                    disabled=cfg.get("disabled", "0") in ("1", "true"),
                ))
            except (TypeError, ValueError):
                continue

        if not result:
            for name in _list_connected_outputs():
                result.append(Monitor(name=name))

        for m in self._monitors:
            if m.name.startswith("fake-") and not any(r.name == m.name for r in result):
                result.append(m)

        return result

    def _add_fake_monitor(self):
        idx = 1
        while any(m.name == f"fake-{idx}" for m in self._monitors):
            idx += 1
        self._monitors.append(Monitor(name=f"fake-{idx}"))
        self._update_combo()
        self._selected = f"fake-{idx}"
        self._load_detail()
        if self._canvas:
            self._canvas.queue_draw()

    def _update_combo(self):
        if self._out_combo is None:
            return
        names = [m.name for m in self._monitors]
        self._out_combo.handler_block_by_func(self._on_output_selected)
        try:
            self._out_combo.set_model(Gtk.StringList.new(names))
            if self._selected in names:
                self._out_combo.set_selected(names.index(self._selected))
        finally:
            self._out_combo.handler_unblock_by_func(self._on_output_selected)

    # ── canvas drawing ──────────────────────────────────────────────

    def _draw_canvas(self, area, cr, width, height):
        if width <= 0 or height <= 0:
            return

        if not self._monitors:
            cr.set_source_rgba(0.05, 0.05, 0.05, 0.4)
            cr.rectangle(0, 0, width, height)
            cr.fill()
            cr.set_source_rgba(0.5, 0.5, 0.5, 0.8)
            cr.select_font_face("Sans", 0, 0)
            cr.set_font_size(14)
            cr.move_to(width / 2 - 90, height / 2)
            cr.show_text("No monitors detected")
            self._draw_ready = False
            return

        min_x = min_y = float("inf")
        max_x = max_y = float("-inf")
        for m in self._monitors:
            lw, lh = m.logical_w(), m.logical_h()
            min_x = min(min_x, m.x)
            min_y = min(min_y, m.y)
            max_x = max(max_x, m.x + lw)
            max_y = max(max_y, m.y + lh)

        total_w = max(max_x - min_x, 1)
        total_h = max(max_y - min_y, 1)

        scale = min(width / total_w, height / total_h) * 0.9
        off_x = (width - total_w * scale) / 2 - min_x * scale
        off_y = (height - total_h * scale) / 2 - min_y * scale

        if self._drag_name:
            scale = self._drag_start_scale
            off_x, off_y = self._drag_start_offset

        self._canvas_scale = scale
        self._canvas_offset = (off_x, off_y)
        self._draw_ready = True

        cr.set_source_rgba(1, 1, 1, 0.03)
        cr.set_line_width(1)
        for gx in range(0, int(width), 40):
            cr.move_to(gx, 0)
            cr.line_to(gx, height)
        for gy in range(0, int(height), 40):
            cr.move_to(0, gy)
            cr.line_to(width, gy)
        cr.stroke()

        for m in self._monitors:
            x = off_x + m.x * scale
            y = off_y + m.y * scale
            w = m.logical_w() * scale
            h = m.logical_h() * scale
            is_sel = m.name == self._selected

            if m.disabled:
                cr.set_source_rgba(0.15, 0.15, 0.15, 1.0)
            elif is_sel:
                cr.set_source_rgba(53 / 255, 132 / 255, 228 / 255, 0.35)
            else:
                cr.set_source_rgba(0.22, 0.22, 0.22, 1.0)
            cr.rectangle(x, y, w, h)
            cr.fill_preserve()

            cr.set_line_width(2.0 if is_sel else 1.5)
            if is_sel:
                cr.set_source_rgba(53 / 255, 132 / 255, 228 / 255, 0.95)
            else:
                cr.set_source_rgba(0.4, 0.4, 0.45, 0.6)
            cr.stroke()

            cr.set_source_rgba(1, 1, 1, 0.95 if is_sel else 0.75)
            cr.select_font_face("Sans", 0, 1)
            fs = max(10, min(16, w / 12))
            cr.set_font_size(fs)
            te = cr.text_extents(m.name)
            cr.move_to(x + w / 2 - te.width / 2, y + h / 2 - fs * 0.3)
            cr.show_text(m.name)

            cr.select_font_face("Sans", 0, 0)
            rs = max(8, min(12, w / 16))
            cr.set_font_size(rs)
            res = f"{m.width}×{m.height}"
            te2 = cr.text_extents(res)
            cr.move_to(x + w / 2 - te2.width / 2, y + h / 2 + rs * 1.2)
            cr.show_text(res)

            cr.set_source_rgba(0.6, 0.6, 0.65, 0.9 if is_sel else 0.6)
            ss = max(7, min(11, w / 20))
            cr.set_font_size(ss)
            stxt = f"×{m.scale:g}" + (" (off)" if m.disabled else "")
            te3 = cr.text_extents(stxt)
            cr.move_to(x + w / 2 - te3.width / 2, y + h / 2 + rs * 1.2 + ss * 1.4)
            cr.show_text(stxt)

    # ── canvas interactions ─────────────────────────────────────────

    def _monitor_at(self, sx: float, sy: float) -> Monitor | None:
        if not self._draw_ready:
            return None
        off_x, off_y = self._canvas_offset
        s = self._canvas_scale
        for m in reversed(self._monitors):
            x = off_x + m.x * s
            y = off_y + m.y * s
            w = m.logical_w() * s
            h = m.logical_h() * s
            if x <= sx <= x + w and y <= sy <= y + h:
                return m
        return None

    def _on_drag_begin(self, gesture, sx, sy):
        m = self._monitor_at(sx, sy)
        if m is None:
            return
        self._drag_name = m.name
        self._drag_current_lx = m.x
        self._drag_current_ly = m.y
        self._drag_start_scale = self._canvas_scale
        self._drag_start_offset = self._canvas_offset
        self._last_dx = 0.0
        self._last_dy = 0.0
        self._selected = m.name
        if self._out_combo:
            names = [x.name for x in self._monitors]
            if m.name in names:
                self._out_combo.handler_block_by_func(self._on_output_selected)
                try:
                    self._out_combo.set_selected(names.index(m.name))
                finally:
                    self._out_combo.handler_unblock_by_func(self._on_output_selected)

    def _on_drag_update(self, gesture, dx, dy):
        if not self._drag_name:
            return
        ddx = dx - self._last_dx
        ddy = dy - self._last_dy
        self._last_dx = dx
        self._last_dy = dy

        s = self._drag_start_scale
        self._drag_current_lx += ddx / s
        self._drag_current_ly += ddy / s

        m = next((x for x in self._monitors if x.name == self._drag_name), None)
        if m is None:
            return

        new_lx = self._drag_current_lx
        new_ly = self._drag_current_ly
        lw = m.logical_w()
        lh = m.logical_h()

        closest_x = SNAP_THRESHOLD + 1
        closest_y = SNAP_THRESHOLD + 1
        snap_x = new_lx
        snap_y = new_ly

        d_left, d_right = new_lx, new_lx + lw
        d_top, d_bottom = new_ly, new_ly + lh

        for other in self._monitors:
            if other.name == self._drag_name:
                continue
            o_l, o_t = other.x, other.y
            o_r = other.x + other.logical_w()
            o_b = other.y + other.logical_h()

            v_near = not (
                d_bottom < o_t - SNAP_THRESHOLD or o_b + SNAP_THRESHOLD < d_top
            )
            h_near = not (
                d_right < o_l - SNAP_THRESHOLD or o_r + SNAP_THRESHOLD < d_left
            )

            if v_near:
                for d_edge, d_start in [(d_left, True), (d_right, False)]:
                    for o_edge, o_start in [(o_l, True), (o_r, False)]:
                        dist = abs(d_edge - o_edge)
                        if dist < closest_x:
                            closest_x = dist
                            snap_x = _snap_axis_origin(o_edge, lw, d_start, o_start)
            if h_near:
                for d_edge, d_start in [(d_top, True), (d_bottom, False)]:
                    for o_edge, o_start in [(o_t, True), (o_b, False)]:
                        dist = abs(d_edge - o_edge)
                        if dist < closest_y:
                            closest_y = dist
                            snap_y = _snap_axis_origin(o_edge, lh, d_start, o_start)

        if closest_x <= SNAP_THRESHOLD:
            new_lx = snap_x
        if closest_y <= SNAP_THRESHOLD:
            new_ly = snap_y

        m.x = new_lx
        m.y = new_ly
        if self._canvas:
            self._canvas.queue_draw()

    def _on_drag_end(self, gesture, dx, dy):
        if not self._drag_name:
            return
        m = next((x for x in self._monitors if x.name == self._drag_name), None)
        self._drag_name = None
        if m is None:
            return
        self._write_monitor(m)
        self._commit("monitor position")
        if self._canvas:
            self._canvas.queue_draw()
        GLib.idle_add(self._deferred_detail_reload)

    def _deferred_detail_reload(self):
        self._load_detail()
        return False

    def _on_canvas_click(self, gesture, n_press, x, y):
        m = self._monitor_at(x, y)
        if m is None:
            return
        self._selected = m.name
        if self._out_combo:
            names = [x.name for x in self._monitors]
            if m.name in names:
                self._out_combo.handler_block_by_func(self._on_output_selected)
                try:
                    self._out_combo.set_selected(names.index(m.name))
                finally:
                    self._out_combo.handler_unblock_by_func(self._on_output_selected)
        GLib.idle_add(self._deferred_detail_reload)
        if self._canvas:
            self._canvas.queue_draw()

    # ── detail panel ────────────────────────────────────────────────

    def _on_output_selected(self, combo, _):
        idx = combo.get_selected()
        if 0 <= idx < len(self._monitors):
            self._selected = self._monitors[idx].name
            self._load_detail()
            if self._canvas:
                self._canvas.queue_draw()

    def _load_detail(self):
        if self._detail_box is None:
            return
        self._suspend_commit = True
        try:
            for c in list(self._detail_box):
                self._detail_box.remove(c)

            m = next((x for x in self._monitors if x.name == self._selected), None)
            if m is None:
                return

            grp = Adw.PreferencesGroup(title=f"Monitor: {m.name}")

            mode_labels = [
                f"{md['width']}×{md['height']}@{md['refresh']:.2f}"
                for md in m.modes
            ] or [f"{m.width}×{m.height}@60.00"]
            mode_row = Adw.ComboRow(
                title="Mode", model=Gtk.StringList.new(mode_labels)
            )
            for i, md in enumerate(m.modes):
                if md["width"] == m.width and md["height"] == m.height:
                    mode_row.set_selected(i)
                    break
            else:
                mode_row.set_selected(0)
            mode_row.connect(
                "notify::selected",
                lambda r, _, mm=m: self._on_mode_changed(mm, r.get_selected()),
            )
            grp.add(mode_row)

            scale_adj = Gtk.Adjustment(
                value=m.scale, lower=0.25, upper=4.0, step_increment=0.05
            )
            scale_row = Adw.SpinRow(
                title="Scale", adjustment=scale_adj, digits=2
            )
            scale_row.connect(
                "notify::value",
                lambda r, _, mm=m: self._on_scale_changed(mm, r.get_value()),
            )
            grp.add(scale_row)

            rot_row = Adw.ComboRow(
                title="Rotation", model=Gtk.StringList.new(ROTATION_LABELS)
            )
            if m.rr in ROTATION_VALUES:
                rot_row.set_selected(ROTATION_VALUES.index(m.rr))
            rot_row.connect(
                "notify::selected",
                lambda r, _, mm=m: self._on_rr_changed(mm, r.get_selected()),
            )
            grp.add(rot_row)

            x_adj = Gtk.Adjustment(
                value=int(m.x), lower=-100000, upper=100000, step_increment=10
            )
            x_row = Adw.SpinRow(title="Position X", adjustment=x_adj, digits=0)
            x_row.connect(
                "notify::value",
                lambda r, _, mm=m: self._on_pos_changed(
                    mm, int(r.get_value()), None
                ),
            )
            grp.add(x_row)

            y_adj = Gtk.Adjustment(
                value=int(m.y), lower=-100000, upper=100000, step_increment=10
            )
            y_row = Adw.SpinRow(title="Position Y", adjustment=y_adj, digits=0)
            y_row.connect(
                "notify::value",
                lambda r, _, mm=m: self._on_pos_changed(
                    mm, None, int(r.get_value())
                ),
            )
            grp.add(y_row)

            vrr_row = Adw.SwitchRow(title="Variable Refresh Rate")
            vrr_row.set_active(m.vrr)
            vrr_row.connect(
                "notify::active",
                lambda r, _, mm=m: self._on_vrr_changed(mm, r.get_active()),
            )
            grp.add(vrr_row)

            dis_row = Adw.SwitchRow(title="Disable Monitor")
            dis_row.set_active(m.disabled)
            dis_row.connect(
                "notify::active",
                lambda r, _, mm=m: self._on_disabled_changed(mm, r.get_active()),
            )
            grp.add(dis_row)

            self._detail_box.append(grp)
        finally:
            self._suspend_commit = False

    # ── mutation callbacks ──────────────────────────────────────────

    def _on_mode_changed(self, m: Monitor, idx: int):
        if not (0 <= idx < len(m.modes)):
            return
        md = m.modes[idx]
        if md["width"] == m.width and md["height"] == m.height:
            return
        m.width = int(md["width"])
        m.height = int(md["height"])
        self._write_monitor(m)
        self._commit("monitor mode")
        if self._canvas:
            self._canvas.queue_draw()

    def _on_scale_changed(self, m: Monitor, value: float):
        value = round(float(value), 3)
        if value == m.scale:
            return
        m.scale = value
        self._write_monitor(m)
        self._commit("monitor scale")
        if self._canvas:
            self._canvas.queue_draw()

    def _on_rr_changed(self, m: Monitor, idx: int):
        if not (0 <= idx < len(ROTATION_VALUES)):
            return
        new_rr = ROTATION_VALUES[idx]
        if new_rr == m.rr:
            return
        m.rr = new_rr
        self._write_monitor(m)
        self._commit("monitor rotation")
        if self._canvas:
            self._canvas.queue_draw()

    def _on_pos_changed(self, m: Monitor, x: int | None, y: int | None):
        changed = False
        if x is not None and x != m.x:
            m.x = x
            changed = True
        if y is not None and y != m.y:
            m.y = y
            changed = True
        if not changed:
            return
        self._write_monitor(m)
        self._commit("monitor position")
        if self._canvas:
            self._canvas.queue_draw()

    def _on_vrr_changed(self, m: Monitor, enabled: bool):
        if enabled == m.vrr:
            return
        m.vrr = enabled
        self._write_monitor(m)
        self._commit("monitor vrr")

    def _on_disabled_changed(self, m: Monitor, disabled: bool):
        if disabled == m.disabled:
            return
        m.disabled = disabled
        self._write_monitor(m)
        self._commit("monitor disabled")
        if self._canvas:
            self._canvas.queue_draw()

    # ── persistence ─────────────────────────────────────────────────

    def _write_monitor(self, m: Monitor):
        rules = self._config.get_all("monitorrule")
        for idx, r in enumerate(rules):
            p = parse_kv_rule(r)
            if _normalize_monitor_name(p.get("name", "")) == m.name:
                # Preserve the original name form (e.g. ^eDP-1$) so we don't
                # rewrite the user's regex anchors just because we saved.
                original_name = p.get("name", m.name)
                new_parts = parse_kv_rule(m.to_rule())
                new_parts["name"] = original_name
                self._config.replace_nth(
                    "monitorrule", idx, build_kv_rule(new_parts)
                )
                return
        # No matching rule — add a new one using the clean name
        self._config.add("monitorrule", m.to_rule())
