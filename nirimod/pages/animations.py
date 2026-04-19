"""Animations page with bezier curve editor."""

from __future__ import annotations

import math

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, GLib, Gtk

from nirimod.kdl_parser import KdlNode, find_or_create, set_child_arg, set_node_flag
from nirimod.pages.base import BasePage, make_toolbar_page


ANIM_NAMES = [
    ("workspace-switch", "Workspace Switch"),
    ("window-open", "Window Open"),
    ("window-close", "Window Close"),
    ("window-movement", "Window Movement"),
    ("window-resize", "Window Resize"),
    ("horizontal-view-movement", "Horizontal View Movement"),
    ("config-notification-open-close", "Config Notification"),
    ("screenshot-ui-open", "Screenshot UI Open"),
    ("overview-open-close", "Overview Open/Close"),
    ("overview-screenshot", "Overview Screenshot"),
]

PRESET_CURVES = {
    "ease": (0.25, 0.1, 0.25, 1.0),
    "ease-in": (0.42, 0.0, 1.0, 1.0),
    "ease-out": (0.0, 0.0, 0.58, 1.0),
    "ease-in-out": (0.42, 0.0, 0.58, 1.0),
    "linear": (0.0, 0.0, 1.0, 1.0),
    "spring": (0.17, 0.67, 0.83, 0.67),
}


class BezierEditor(Gtk.DrawingArea):
    """Interactive cubic Bézier curve editor with animated preview ball."""

    def __init__(self, on_changed=None):
        super().__init__()
        self._cp = [0.25, 0.1, 0.25, 1.0]  # x1,y1,x2,y2
        self._on_changed = on_changed
        self._dragging: int | None = None  # 0=p1, 1=p2
        self._ball_t = 0.0
        self._ball_dir = 1
        self._anim_id: int | None = None

        self.set_content_width(220)
        self.set_content_height(180)
        self.set_draw_func(self._draw)

        motion = Gtk.EventControllerMotion()
        motion.connect("motion", self._on_motion)
        self.add_controller(motion)

        click = Gtk.GestureClick()
        click.connect("pressed", self._on_press)
        click.connect("released", self._on_release)
        self.add_controller(click)

        self._start_anim()

    def set_curve(self, x1, y1, x2, y2):
        self._cp = [x1, y1, x2, y2]
        self.queue_draw()

    def get_curve(self):
        return tuple(self._cp)

    def _start_anim(self):
        self._anim_id = GLib.timeout_add(16, self._tick_anim)

    def _tick_anim(self):
        self._ball_t += 0.012 * self._ball_dir
        if self._ball_t >= 1.0:
            self._ball_t = 1.0
            self._ball_dir = -1
        elif self._ball_t <= 0.0:
            self._ball_t = 0.0
            self._ball_dir = 1
        self.queue_draw()
        return GLib.SOURCE_CONTINUE

    def _bezier_pt(self, t):
        x1, y1, x2, y2 = self._cp
        # Cubic bezier from (0,0) to (1,1) with controls (x1,y1), (x2,y2)
        mt = 1 - t
        bx = 3 * mt * mt * t * x1 + 3 * mt * t * t * x2 + t * t * t
        by = 3 * mt * mt * t * y1 + 3 * mt * t * t * y2 + t * t * t
        return bx, by

    def _canvas_to_cp(self, cx, cy, W, H, pad=20):
        """Convert canvas coords to bezier control point (0-1 range)."""
        x = (cx - pad) / (W - 2 * pad)
        y = 1.0 - (cy - pad) / (H - 2 * pad)
        return max(0.0, min(1.0, x)), max(-0.5, min(1.5, y))

    def _cp_to_canvas(self, x, y, W, H, pad=20):
        cx = pad + x * (W - 2 * pad)
        cy = pad + (1.0 - y) * (H - 2 * pad)
        return cx, cy

    def _draw(self, area, cr, W, H):
        pad = 20

        cr.set_source_rgba(0.08, 0.08, 0.08, 1.0)
        cr.rectangle(0, 0, W, H)
        cr.fill()
        cr.set_source_rgba(0.2, 0.2, 0.22, 0.4)
        cr.set_line_width(0.5)
        for i in range(5):
            gx = pad + i * (W - 2 * pad) / 4
            gy = pad + i * (H - 2 * pad) / 4
            cr.move_to(gx, pad)
            cr.line_to(gx, H - pad)
            cr.stroke()
            cr.move_to(pad, gy)
            cr.line_to(W - pad, gy)
            cr.stroke()

        x1, y1, x2, y2 = self._cp
        px1, py1 = self._cp_to_canvas(x1, y1, W, H, pad)
        px2, py2 = self._cp_to_canvas(x2, y2, W, H, pad)
        start = self._cp_to_canvas(0, 0, W, H, pad)
        end = self._cp_to_canvas(1, 1, W, H, pad)

        cr.set_source_rgba(0.2, 0.2, 0.25, 0.4)
        cr.set_line_width(1.0)
        cr.move_to(*start)
        cr.line_to(px1, py1)
        cr.stroke()
        cr.move_to(*end)
        cr.line_to(px2, py2)
        cr.stroke()

        # Bezier path
        cr.set_source_rgba(0.3, 0.7, 1.0, 0.9)
        cr.set_line_width(2.5)
        cr.move_to(*start)
        cr.curve_to(px1, py1, px2, py2, *end)
        cr.stroke()

        bx_01, by_01 = self._bezier_pt(self._ball_t)
        bx_c, by_c = self._cp_to_canvas(bx_01, by_01, W, H, pad)
        cr.set_source_rgba(1.0, 0.6, 0.2, 0.95)
        cr.arc(bx_c, by_c, 5, 0, 2 * math.pi)
        cr.fill()

        for px, py, color in [
            (px1, py1, (0.4, 1.0, 0.5, 1.0)),
            (px2, py2, (1.0, 0.4, 0.5, 1.0)),
        ]:
            cr.set_source_rgba(*color)
            cr.arc(px, py, 6, 0, 2 * math.pi)
            cr.fill()
            cr.set_source_rgba(1, 1, 1, 0.5)
            cr.set_line_width(1.5)
            cr.arc(px, py, 6, 0, 2 * math.pi)
            cr.stroke()

    def _hit_cp(self, cx, cy, W, H, pad=20):
        x1, y1, x2, y2 = self._cp
        px1, py1 = self._cp_to_canvas(x1, y1, W, H, pad)
        px2, py2 = self._cp_to_canvas(x2, y2, W, H, pad)
        if math.hypot(cx - px1, cy - py1) < 12:
            return 0
        if math.hypot(cx - px2, cy - py2) < 12:
            return 1
        return None

    def _on_press(self, gesture, _n, x, y):
        W = self.get_width()
        H = self.get_height()
        self._dragging = self._hit_cp(x, y, W, H)

    def _on_release(self, gesture, _n, x, y):
        self._dragging = None

    def _on_motion(self, controller, x, y):
        if self._dragging is None:
            return
        W = self.get_width()
        H = self.get_height()
        cpx, cpy = self._canvas_to_cp(x, y, W, H)
        if self._dragging == 0:
            self._cp[0] = cpx
            self._cp[1] = cpy
        else:
            self._cp[2] = cpx
            self._cp[3] = cpy
        self.queue_draw()
        if self._on_changed:
            self._on_changed(*self._cp)


class AnimationsPage(BasePage):
    def build(self) -> Gtk.Widget:
        tb, _, _, content = self._make_toolbar_page("Animations")
        self._content = content

        anim_node = find_or_create(self._nodes, "animations")

        # Global off toggle
        off_grp = Adw.PreferencesGroup(title="Global")
        off_row = Adw.SwitchRow(title="Enable Animations")
        off_row.set_active(anim_node.get_child("off") is None)
        off_row.connect(
            "notify::active", lambda r, _: self._toggle_all(not r.get_active())
        )
        off_grp.add(off_row)

        slowdown_val = float(anim_node.child_arg("slowdown") or 1.0)
        slowdown_adj = Gtk.Adjustment(
            value=slowdown_val, lower=0.1, upper=10.0, step_increment=0.1
        )
        slowdown_row = Adw.SpinRow(
            title="Global Slowdown Factor", adjustment=slowdown_adj, digits=1
        )

        slowdown_row._last_val = slowdown_val

        def _on_slowdown_changed(r, _):
            new_val = float(r.get_value())
            # Use abs difference to avoid float comparison issues
            if abs(new_val - getattr(r, "_last_val", 0.0)) > 0.01:
                r._last_val = new_val
                self._set_anim("slowdown", new_val)

        slowdown_row.connect("notify::value", _on_slowdown_changed)
        off_grp.add(slowdown_row)
        content.append(off_grp)

        bezier_grp = Adw.PreferencesGroup(title="Easing Curve Editor")
        
        card = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
        card.add_css_class("card")
        card.set_margin_bottom(12)

        # Editor side
        edit_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        edit_vbox.set_margin_start(16)
        edit_vbox.set_margin_top(16)
        edit_vbox.set_margin_bottom(16)
        
        self._bezier_editor = BezierEditor(on_changed=self._on_bezier_changed)
        edit_vbox.append(self._bezier_editor)

        coords_lbl = Gtk.Label(label="0.25, 0.1, 0.25, 1.0")
        coords_lbl.add_css_class("monospace")
        coords_lbl.add_css_class("dim-label")
        coords_lbl.set_selectable(True)
        self._coords_lbl = coords_lbl
        edit_vbox.append(coords_lbl)
        
        card.append(edit_vbox)

        # Presets side
        presets_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        presets_vbox.set_margin_end(16)
        presets_vbox.set_margin_top(16)
        presets_vbox.set_margin_bottom(16)
        presets_vbox.set_hexpand(True)

        preset_title = Gtk.Label(label="Presets", xalign=0)
        preset_title.add_css_class("heading")
        presets_vbox.append(preset_title)

        flow = Gtk.FlowBox()
        flow.set_selection_mode(Gtk.SelectionMode.NONE)
        flow.set_max_children_per_line(2)
        flow.set_valign(Gtk.Align.START)

        for name, curve in PRESET_CURVES.items():
            btn = Gtk.Button(label=name)
            btn.add_css_class("flat")
            btn.add_css_class("pill")
            btn.connect("clicked", lambda b, c=curve, n=name: self._apply_preset(c, n))
            flow.append(btn)

        presets_vbox.append(flow)
        card.append(presets_vbox)

        bezier_grp.add(card)
        content.append(bezier_grp)

        # Per-animation rows
        anim_list_grp = Adw.PreferencesGroup(title="Animation Categories")
        for anim_key, anim_label in ANIM_NAMES:
            row = self._build_anim_row(anim_key, anim_label, anim_node)
            anim_list_grp.add(row)
        content.append(anim_list_grp)

        return tb

    def _apply_preset(self, curve: tuple, name: str):
        self._bezier_editor.set_curve(*curve)
        self._update_coords_label()

    def _on_bezier_changed(self, x1, y1, x2, y2):
        self._update_coords_label()

    def _update_coords_label(self):
        x1, y1, x2, y2 = self._bezier_editor.get_curve()
        self._coords_lbl.set_label(f"{x1:.3f}, {y1:.3f}, {x2:.3f}, {y2:.3f}")

    def _build_anim_row(
        self, key: str, label: str, anim_node: KdlNode
    ) -> Adw.ExpanderRow:
        grp = Adw.ExpanderRow(title=label)
        grp.add_css_class("nm-expander")
        an = anim_node.get_child(key)

        enabled_row = Adw.SwitchRow(title="Enabled")
        enabled_row.set_active(an is not None and an.get_child("off") is None)
        enabled_row.connect(
            "notify::active",
            lambda r, _, k=key: self._set_anim_enabled(k, r.get_active()),
        )
        grp.add_row(enabled_row)

        duration = an.child_arg("duration-ms") if an else 250
        dur_val = int(duration) if duration else 250
        dur_adj = Gtk.Adjustment(value=dur_val, lower=10, upper=2000, step_increment=10)
        dur_row = Adw.SpinRow(title="Duration (ms)", adjustment=dur_adj, digits=0)

        dur_row._last_val = dur_val

        def _on_dur_changed(r, _, k=key):
            new_val = int(r.get_value())
            if new_val != getattr(r, "_last_val", None):
                r._last_val = new_val
                self._set_anim_prop(k, "duration-ms", new_val)

        dur_row.connect("notify::value", _on_dur_changed)
        grp.add_row(dur_row)

        # Apply bezier button
        apply_btn = Gtk.Button(label="Apply Editor Curve")
        apply_btn.add_css_class("flat")
        apply_btn.set_valign(Gtk.Align.CENTER)
        
        # Determine current curve for subtitle
        easing = an.get_child("easing") if an else None
        current_curve = ""
        if easing and easing.child_arg("bezier"):
            current_curve = f"bezier {easing.child_arg('bezier')}"
        elif easing and easing.args:
            current_curve = str(easing.args[0])
            
        apply_row = Adw.ActionRow(title="Easing Curve", subtitle=current_curve if current_curve else "Default")
        apply_btn.connect("clicked", lambda *_, k=key, ar=apply_row: self._apply_bezier_to_anim(k, ar))
        apply_row.add_suffix(apply_btn)
        grp.add_row(apply_row)

        return grp

    def _toggle_all(self, off: bool):
        anim = find_or_create(self._nodes, "animations")
        set_node_flag(anim, "off", off)
        self._commit("animations off")

    def _set_anim(self, key: str, value):
        anim = find_or_create(self._nodes, "animations")
        set_child_arg(anim, key, value)
        self._commit(f"animations {key}")

    def _set_anim_enabled(self, anim_key: str, enabled: bool):
        anim = find_or_create(self._nodes, "animations")
        an = anim.get_child(anim_key)
        if not enabled:
            if an is None:
                an = KdlNode(anim_key)
                anim.children.append(an)
            set_node_flag(an, "off", True)
        else:
            if an:
                from nirimod.kdl_parser import remove_child

                remove_child(an, "off")
        self._commit(f"animation {anim_key} enabled")

    def _set_anim_prop(self, anim_key: str, prop: str, value):
        anim = find_or_create(self._nodes, "animations")
        an = anim.get_child(anim_key)
        if an is None:
            an = KdlNode(anim_key)
            anim.children.append(an)
        set_child_arg(an, prop, value)
        self._commit(f"animation {anim_key} {prop}")

    def _apply_bezier_to_anim(self, anim_key: str, apply_row: Adw.ActionRow = None):
        x1, y1, x2, y2 = self._bezier_editor.get_curve()
        anim = find_or_create(self._nodes, "animations")
        an = anim.get_child(anim_key)
        if an is None:
            an = KdlNode(anim_key)
            anim.children.append(an)
        easing = an.get_child("easing")
        if easing is None:
            easing = KdlNode("easing")
            an.children.append(easing)
            
        curve_str = f"{x1:.3f} {y1:.3f} {x2:.3f} {y2:.3f}"
        set_child_arg(easing, "bezier", curve_str)
        self._commit(f"animation {anim_key} bezier")
        self.show_toast(f"Bezier applied to {anim_key}")
        
        if apply_row:
            apply_row.set_subtitle(f"bezier {curve_str}")
