"""Outputs / Monitors page with interactive canvas."""

from __future__ import annotations

from typing import TYPE_CHECKING

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

import math


def _rounded_rect(cr, x, y, w, h, r):
    cr.new_sub_path()
    cr.arc(x + w - r, y + r, r, -math.pi / 2, 0)
    cr.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
    cr.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
    cr.arc(x + r, y + r, r, math.pi, 3 * math.pi / 2)
    cr.close_path()


from gi.repository import Adw, Gtk

from nirimod import niri_ipc
from nirimod.kdl_parser import KdlNode, set_child_arg, safe_switch_connect
from nirimod.pages.base import BasePage

if TYPE_CHECKING:
    from nirimod.window import NiriModWindow

TRANSFORMS = [
    "normal",
    "90",
    "180",
    "270",
    "flipped",
    "flipped-90",
    "flipped-180",
    "flipped-270",
]


class OutputsPage(BasePage):
    def __init__(self, window: "NiriModWindow"):
        super().__init__(window)
        self._outputs: list[dict] = []
        self._current_out: dict | None = None

        self._canvas: Gtk.DrawingArea | None = None
        self._drag_output: str | None = None
        self._drag_offset: tuple[float, float] = (0, 0)

    def build(self) -> Gtk.Widget:
        tb, header, scroll, content = self._make_toolbar_page("Outputs")

        refresh_btn = Gtk.Button(icon_name="view-refresh-symbolic")
        refresh_btn.set_tooltip_text("Reload outputs from niri")
        refresh_btn.add_css_class("flat")
        refresh_btn.connect("clicked", lambda *_: self.refresh())
        header.pack_end(refresh_btn)

        canvas_frame = Gtk.Frame()
        canvas_frame.add_css_class("card")
        canvas_frame.set_margin_bottom(8)

        self._canvas = Gtk.DrawingArea()
        self._canvas.set_content_height(350)
        self._canvas.set_draw_func(self._draw_canvas)
        canvas_frame.set_child(self._canvas)
        content.append(canvas_frame)

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
        sel_group = Adw.PreferencesGroup()
        sel_group.add(self._out_combo)
        content.append(sel_group)

        self._detail_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        content.append(self._detail_box)

        self.refresh()
        return tb

    def refresh(self):
        def _on_got_outputs(outputs):
            self._outputs = outputs
            names = [o.get("name", "?") for o in self._outputs]
            model = Gtk.StringList.new(names)
            self._out_combo.set_model(model)
            if self._outputs:
                self._load_output_detail(self._outputs[0])
            if self._canvas:
                self._canvas.queue_draw()
            # Rebuild search index as the detail rows are now populated
            if hasattr(self._win, "_build_search_index"):
                self._win._build_search_index()

        niri_ipc.get_outputs(_on_got_outputs)

    # Canvas drawing

    def _draw_canvas(self, area, cr, width, height):
        if not self._outputs:
            cr.set_source_rgba(0.05, 0.05, 0.05, 0.4)
            cr.rectangle(0, 0, width, height)
            cr.fill()
            cr.set_source_rgba(0.5, 0.5, 0.5, 0.8)
            cr.select_font_face("Sans", 0, 0)
            cr.set_font_size(14)
            cr.move_to(width / 2 - 80, height / 2)
            cr.show_text("No outputs detected")
            return

        min_x = min_y = float("inf")
        max_x = max_y = float("-inf")
        for o in self._outputs:
            pos = o.get("logical", {})
            lx = pos.get("x", 0)
            ly = pos.get("y", 0)
            lw = pos.get("width", 1920)
            lh = pos.get("height", 1080)
            min_x = min(min_x, lx)
            min_y = min(min_y, ly)
            max_x = max(max_x, lx + lw)
            max_y = max(max_y, ly + lh)

        if min_x == float("inf"):
            min_x = min_y = 0
            max_x = 1920
            max_y = 1080

        bb_w = max_x - min_x
        bb_h = max_y - min_y

        scale = min(width / max(bb_w, 1), height / max(bb_h, 1)) * 0.85
        off_x = (width - bb_w * scale) / 2 - min_x * scale
        off_y = (height - bb_h * scale) / 2 - min_y * scale

        if self._drag_output and hasattr(self, "_drag_start_scale"):
            scale = self._drag_start_scale
            off_x = self._drag_start_offset[0]
            off_y = self._drag_start_offset[1]

        self._canvas_scale = scale
        self._canvas_offset = (off_x, off_y)
        self._canvas_pixel_w = width
        self._canvas_pixel_h = height

        # grid background
        cr.set_source_rgba(1, 1, 1, 0.03)
        cr.set_line_width(1)
        grid_size = 40
        for gx in range(0, int(width), grid_size):
            cr.move_to(gx, 0)
            cr.line_to(gx, height)
        for gy in range(0, int(height), grid_size):
            cr.move_to(0, gy)
            cr.line_to(width, gy)
        cr.stroke()

        for i, o in enumerate(self._outputs):
            pos = o.get("logical", {})
            x = off_x + pos.get("x", 0) * scale
            y = off_y + pos.get("y", 0) * scale
            w = pos.get("width", 1920) * scale
            h = pos.get("height", 1080) * scale

            is_sel = o.get("name") == (
                self._current_out.get("name") if self._current_out else None
            )

            radius = min(w, h) * 0.05
            radius = max(4, min(radius, 12))

            cr.set_source_rgba(0, 0, 0, 0.25)
            _rounded_rect(cr, x + 4, y + 6, w, h, radius)
            cr.fill()

            if is_sel:
                cr.set_source_rgba(0.2, 0.5, 0.9, 1.0)
            else:
                cr.set_source_rgba(0.15, 0.15, 0.17, 1.0)
            _rounded_rect(cr, x, y, w, h, radius)
            cr.fill()

            bezel = max(2, min(w, h) * 0.02)
            cr.set_source_rgba(0.1, 0.1, 0.12, 1.0)
            _rounded_rect(
                cr, x + bezel, y + bezel, w - bezel * 2, h - bezel * 2, radius * 0.8
            )
            cr.fill()

            cr.set_source_rgba(1, 1, 1, 0.04)
            _rounded_rect(
                cr,
                x + bezel,
                y + bezel,
                w - bezel * 2,
                (h - bezel * 2) * 0.4,
                radius * 0.8,
            )
            cr.fill()

            name = o.get("name", f"Output {i}")
            mode_idx = o.get("current_mode")
            modes = o.get("modes", [])
            mode = (
                modes[mode_idx]
                if isinstance(mode_idx, int) and 0 <= mode_idx < len(modes)
                else {}
            )
            out_scale = o.get("logical", {}).get("scale", 1.0)
            res = f"{mode.get('width', '?')}×{mode.get('height', '?')}"
            scale_text = f"Scale: {out_scale}x"

            cr.set_source_rgba(1, 1, 1, 0.95 if is_sel else 0.7)

            cr.select_font_face("Sans", 0, 1)
            font_size = max(10, min(16, w / 10))
            cr.set_font_size(font_size)
            te = cr.text_extents(name)
            cr.move_to(x + w / 2 - te.width / 2, y + h / 2 - font_size * 0.3)
            cr.show_text(name)

            cr.select_font_face("Sans", 0, 0)
            res_size = max(8, min(12, w / 15))
            cr.set_font_size(res_size)
            te2 = cr.text_extents(res)
            cr.move_to(x + w / 2 - te2.width / 2, y + h / 2 + res_size * 1.2)
            cr.show_text(res)

            cr.set_source_rgba(0.6, 0.6, 0.65, 0.9 if is_sel else 0.6)
            scale_size = max(7, min(11, w / 18))
            cr.set_font_size(scale_size)
            te3 = cr.text_extents(scale_text)
            cr.move_to(
                x + w / 2 - te3.width / 2, y + h / 2 + res_size * 1.2 + scale_size * 1.4
            )
            cr.show_text(scale_text)

    def _on_drag_begin(self, gesture, sx, sy):
        if not hasattr(self, "_canvas_scale"):
            return
        scale = self._canvas_scale
        ox, oy = self._canvas_offset
        for o in reversed(self._outputs):
            pos = o.get("logical", {})
            x = ox + pos.get("x", 0) * scale
            y = oy + pos.get("y", 0) * scale
            w = pos.get("width", 1920) * scale
            h = pos.get("height", 1080) * scale
            if x <= sx <= x + w and y <= sy <= y + h:
                self._drag_output = o["name"]
                self._last_dx = 0
                self._last_dy = 0
                self._drag_current_lx = pos.get("x", 0)
                self._drag_current_ly = pos.get("y", 0)
                self._drag_start_scale = scale
                self._drag_start_offset = (ox, oy)
                return

    def _on_drag_update(self, gesture, dx, dy):
        if not self._drag_output or not hasattr(self, "_canvas_scale"):
            return

        scale = getattr(self, "_drag_start_scale", self._canvas_scale)
        delta_dx = dx - getattr(self, "_last_dx", 0)
        delta_dy = dy - getattr(self, "_last_dy", 0)
        self._last_dx = dx
        self._last_dy = dy

        self._drag_current_lx += delta_dx / scale
        self._drag_current_ly += delta_dy / scale

        new_lx = round(self._drag_current_lx / 10) * 10
        new_ly = round(self._drag_current_ly / 10) * 10

        drag_o = next(
            (o for o in self._outputs if o.get("name") == self._drag_output), None
        )
        if not drag_o:
            return

        drag_w = drag_o.get("logical", {}).get("width", 1920)
        drag_h = drag_o.get("logical", {}).get("height", 1080)

        drag_scale_u = drag_o.get("logical", {}).get("scale", 1.0)
        mode_idx_u = drag_o.get("current_mode")
        modes_u = drag_o.get("modes", [])
        m_u = (
            modes_u[mode_idx_u]
            if isinstance(mode_idx_u, int) and 0 <= mode_idx_u < len(modes_u)
            else {}
        )
        pw_u = m_u.get("width", 1920)
        ph_u = m_u.get("height", 1080)
        t_u = drag_o.get("logical", {}).get("transform", "normal")
        t_str_u = str(t_u).lower().replace("_", "-")
        if t_str_u in ["90", "270", "flipped-90", "flipped-270"]:
            pw_u, ph_u = ph_u, pw_u

        exact_drag_w = pw_u / drag_scale_u
        exact_drag_h = ph_u / drag_scale_u

        max_allowed_x = 32768
        max_allowed_y = 32768

        new_lx = max(0, min(max_allowed_x - drag_w, new_lx))
        new_ly = max(0, min(max_allowed_y - drag_h, new_ly))
        snap_dist = 40 / scale

        import math

        # Snapping to edges
        for o in self._outputs:
            if o.get("name") == self._drag_output:
                continue
            ox2 = o.get("logical", {}).get("x", 0)
            oy2 = o.get("logical", {}).get("y", 0)

            # Use exact fractional dimensions to prevent Niri overlap rejection
            scale2 = o.get("logical", {}).get("scale", 1.0)
            mode_idx = o.get("current_mode")
            modes = o.get("modes", [])
            m = (
                modes[mode_idx]
                if isinstance(mode_idx, int) and 0 <= mode_idx < len(modes)
                else {}
            )
            pw2 = m.get("width", 1920)
            ph2 = m.get("height", 1080)

            t2 = o.get("logical", {}).get("transform", "normal")
            t_str2 = str(t2).lower().replace("_", "-")
            if t_str2 in ["90", "270", "flipped-90", "flipped-270"]:
                pw2, ph2 = ph2, pw2

            exact_w = pw2 / scale2
            exact_h = ph2 / scale2

            ow2 = o.get("logical", {}).get("width", math.ceil(exact_w))
            oh2 = o.get("logical", {}).get("height", math.ceil(exact_h))

            y_overlaps = not (
                new_ly + drag_h < oy2 - snap_dist or oy2 + oh2 + snap_dist < new_ly
            )
            x_overlaps = not (
                new_lx + drag_w < ox2 - snap_dist or ox2 + ow2 + snap_dist < new_lx
            )

            if y_overlaps:
                if abs((new_lx + drag_w) - ox2) < snap_dist:
                    new_lx = math.floor(ox2 - exact_drag_w)
                elif abs(new_lx - (ox2 + exact_w)) < snap_dist:
                    new_lx = math.ceil(ox2 + exact_w)
                elif abs(new_lx - ox2) < snap_dist:
                    new_lx = ox2
                elif abs((new_lx + drag_w) - (ox2 + exact_w)) < snap_dist:
                    new_lx = math.ceil(ox2 + exact_w) - math.ceil(exact_drag_w)

            if x_overlaps:
                if abs((new_ly + drag_h) - oy2) < snap_dist:
                    new_ly = math.floor(oy2 - exact_drag_h)
                elif abs(new_ly - (oy2 + exact_h)) < snap_dist:
                    new_ly = math.ceil(oy2 + exact_h)
                elif abs(new_ly - oy2) < snap_dist:
                    new_ly = oy2
                elif abs((new_ly + drag_h) - (oy2 + exact_h)) < snap_dist:
                    new_ly = math.ceil(oy2 + exact_h) - math.ceil(exact_drag_h)

        if "logical" not in drag_o:
            drag_o["logical"] = {}
        drag_o["logical"]["x"] = new_lx
        drag_o["logical"]["y"] = new_ly

        if self._canvas:
            self._canvas.queue_draw()

    def _on_drag_end(self, gesture, dx, dy):
        if self._drag_output:
            drag_o = next(
                (o for o in self._outputs if o.get("name") == self._drag_output), None
            )
            if drag_o:
                new_lx = drag_o.get("logical", {}).get("x", 0)
                new_ly = drag_o.get("logical", {}).get("y", 0)
                drag_w = drag_o.get("logical", {}).get("width", 1920)
                drag_h = drag_o.get("logical", {}).get("height", 1080)

                max_allowed_x = 32768
                max_allowed_y = 32768

                new_lx = max(0, min(max_allowed_x - drag_w, new_lx))
                new_ly = max(0, min(max_allowed_y - drag_h, new_ly))

                drag_o["logical"]["x"] = new_lx
                drag_o["logical"]["y"] = new_ly
                if self._canvas:
                    self._canvas.queue_draw()

            self._apply_position(self._drag_output)
            self._drag_output = None

    def _on_canvas_click(self, gesture, n_press, x, y):
        if not hasattr(self, "_canvas_scale"):
            return
            
        scale = self._canvas_scale
        ox, oy = self._canvas_offset
        
        for i, o in reversed(list(enumerate(self._outputs))):
            pos = o.get("logical", {})
            mx = ox + pos.get("x", 0) * scale
            my = oy + pos.get("y", 0) * scale
            mw = pos.get("width", 1920) * scale
            mh = pos.get("height", 1080) * scale
            
            if mx <= x <= mx + mw and my <= y <= my + mh:
                self._out_combo.set_selected(i)
                return

    def _apply_position(self, name: str):
        o = next((x for x in self._outputs if x["name"] == name), None)
        if not o:
            return
        pos = o.get("logical", {})

        out_node = self._get_or_create_out_node(name)
        pos_node = out_node.get_child("position")
        if pos_node is None:
            pos_node = KdlNode(name="position")
            out_node.children.append(pos_node)
        pos_node.props["x"] = int(round(pos.get("x", 0)))
        pos_node.props["y"] = int(round(pos.get("y", 0)))

        if self._current_out and self._current_out.get("name") == name:
            if hasattr(self, "_pos_x_adj"):
                self._pos_x_adj.set_value(pos.get("x", 0))
            if hasattr(self, "_pos_y_adj"):
                self._pos_y_adj.set_value(pos.get("y", 0))

        self._commit("output position")

    def _on_output_selected(self, combo, _):
        idx = combo.get_selected()
        if 0 <= idx < len(self._outputs):
            self._load_output_detail(self._outputs[idx])
            # Rebuild search index as the detail rows have changed
            if hasattr(self._win, "_build_search_index"):
                self._win._build_search_index()

    def _load_output_detail(self, output: dict):
        self._current_out = output
        for child in list(self._detail_box):
            self._detail_box.remove(child)

        name = output.get("name", "?")
        nodes = self._nodes
        out_node = next(
            (n for n in nodes if n.name == "output" and n.args and n.args[0] == name),
            None,
        )

        modes = output.get("modes", [])
        mode_strs = [
            f"{m.get('width', 0)}×{m.get('height', 0)}@{m.get('refresh_rate', 0) / 1000:.3f}"
            for m in modes
        ]
        mode_model = Gtk.StringList.new(mode_strs)
        mode_row = Adw.ComboRow(title="Resolution &amp; Refresh Rate")
        mode_row.set_model(mode_model)
        mode_idx = output.get("current_mode")
        cur_mode = (
            modes[mode_idx]
            if isinstance(mode_idx, int) and 0 <= mode_idx < len(modes)
            else {}
        )
        cur_str = f"{cur_mode.get('width', 0)}×{cur_mode.get('height', 0)}@{cur_mode.get('refresh_rate', 0) / 1000:.3f}"
        if cur_str in mode_strs:
            mode_row.set_selected(mode_strs.index(cur_str))
        mode_row.connect(
            "notify::selected",
            lambda r, _: self._on_mode_changed(name, modes, r.get_selected()),
        )

        scale_val = round(output.get("logical", {}).get("scale", 1.0), 3)
        scale_adj = Gtk.Adjustment(
            value=scale_val,
            lower=0.25,
            upper=4.0,
            step_increment=0.05,
        )
        scale_row = Adw.SpinRow(title="Scale", adjustment=scale_adj, digits=2)
        scale_row.connect(
            "notify::value",
            lambda r, _: self._set_output_prop(name, "scale", r.get_value()),
        )

        t_model = Gtk.StringList.new(TRANSFORMS)
        transform_row = Adw.ComboRow(title="Transform", model=t_model)
        cur_t = output.get("logical", {}).get("transform", "normal")
        cur_t_norm = str(cur_t).lower().replace("_", "-") if cur_t else "normal"
        if cur_t_norm in TRANSFORMS:
            transform_row.set_selected(TRANSFORMS.index(cur_t_norm))
        transform_row.connect(
            "notify::selected",
            lambda r, _: self._set_output_prop(
                name, "transform", TRANSFORMS[r.get_selected()]
            ),
        )

        px = output.get("logical", {}).get("x", 0)
        py = output.get("logical", {}).get("y", 0)
        px_adj = Gtk.Adjustment(value=px, lower=0, upper=32768, step_increment=1)
        py_adj = Gtk.Adjustment(value=py, lower=0, upper=32768, step_increment=1)
        self._pos_x_adj = px_adj
        self._pos_y_adj = py_adj
        pos_x_row = Adw.SpinRow(title="Position X", adjustment=px_adj, digits=0)
        pos_y_row = Adw.SpinRow(title="Position Y", adjustment=py_adj, digits=0)
        pos_x_row.connect(
            "notify::value",
            lambda r, _: self._set_output_pos(
                name, int(r.get_value()), int(py_adj.get_value())
            ),
        )
        pos_y_row.connect(
            "notify::value",
            lambda r, _: self._set_output_pos(
                name, int(px_adj.get_value()), int(r.get_value())
            ),
        )

        vrr_row = Adw.SwitchRow(title="Variable Refresh Rate (VRR)")
        vrr_val = (
            (out_node.get_child("variable-refresh-rate") is not None)
            if out_node
            else False
        )
        vrr_row.set_active(vrr_val)
        safe_switch_connect(
            vrr_row,
            vrr_val,
            lambda enabled: self._set_output_flag(
                name, "variable-refresh-rate", enabled
            ),
        )

        off_row = Adw.SwitchRow(title="Disable Output")
        off_val = (out_node.get_child("off") is not None) if out_node else False
        off_row.set_active(off_val)
        safe_switch_connect(
            off_row,
            off_val,
            lambda enabled: self._set_output_flag(name, "off", enabled),
        )

        grp = Adw.PreferencesGroup(title=f"Output: {name}")
        for r in [
            mode_row,
            scale_row,
            transform_row,
            pos_x_row,
            pos_y_row,
            vrr_row,
            off_row,
        ]:
            grp.add(r)
        self._detail_box.append(grp)

        if self._canvas:
            self._canvas.queue_draw()

    def _ensure_output_fields(self, out_node: KdlNode, name: str):
        manual_out = None
        try:
            manual_nodes = self._nodes
            if manual_nodes:
                manual_out = next(
                    (
                        n
                        for n in manual_nodes
                        if n.name == "output" and n.args and n.args[0] == name
                    ),
                    None,
                )
        except Exception:
            pass

        if manual_out:
            if out_node.get_child("mode") is None:
                m = manual_out.child_arg("mode")
                if m:
                    set_child_arg(out_node, "mode", m)
            if out_node.get_child("scale") is None:
                s = manual_out.child_arg("scale")
                if s is not None:
                    set_child_arg(out_node, "scale", s)
            if out_node.get_child("transform") is None:
                t = manual_out.child_arg("transform")
                if t:
                    set_child_arg(out_node, "transform", t)
            if out_node.get_child("position") is None:
                pos_node = manual_out.get_child("position")
                if pos_node:
                    new_pos = KdlNode(name="position", props=pos_node.props.copy())
                    out_node.children.append(new_pos)

        o = next((x for x in self._outputs if x.get("name") == name), None)
        if o:
            if out_node.get_child("mode") is None:
                mode_idx = o.get("current_mode")
                modes = o.get("modes", [])
                if isinstance(mode_idx, int) and 0 <= mode_idx < len(modes):
                    m = modes[mode_idx]
                    mode_str = f"{m.get('width', 0)}x{m.get('height', 0)}@{m.get('refresh_rate', 0) / 1000:.3f}"
                    set_child_arg(out_node, "mode", mode_str)
            if out_node.get_child("scale") is None:
                set_child_arg(out_node, "scale", o.get("logical", {}).get("scale", 1.0))
            if out_node.get_child("transform") is None:
                t = o.get("logical", {}).get("transform", "normal")
                t = str(t).lower().replace("_", "-") if t else "normal"
                if t not in TRANSFORMS:
                    t = "normal"
                set_child_arg(out_node, "transform", t)
            pos_node = out_node.get_child("position")
            if pos_node is None:
                pos_node = KdlNode(name="position")
                out_node.children.append(pos_node)
                pos_node.props["x"] = o.get("logical", {}).get("x", 0)
                pos_node.props["y"] = o.get("logical", {}).get("y", 0)

    def _get_or_create_out_node(self, name: str) -> KdlNode:
        nodes = self._nodes
        out_node = next(
            (n for n in nodes if n.name == "output" and n.args and n.args[0] == name),
            None,
        )
        is_new = out_node is None
        if out_node is None:
            out_node = KdlNode(name="output", args=[name])
            nodes.append(out_node)

        assert out_node is not None

        if is_new:
            self._ensure_output_fields(out_node, name)

        order = {"mode": 0, "scale": 1, "transform": 2, "position": 3}
        out_node.children.sort(key=lambda c: order.get(c.name, 999))

        return out_node

    def _update_logical_dims(self, o: dict):
        if "logical" not in o:
            o["logical"] = {}
        mode_idx = o.get("current_mode")
        modes = o.get("modes", [])
        m = (
            modes[mode_idx]
            if isinstance(mode_idx, int) and 0 <= mode_idx < len(modes)
            else {}
        )
        pw = m.get("width", 1920)
        ph = m.get("height", 1080)

        scale = o["logical"].get("scale", 1.0)
        if scale <= 0:
            scale = 1.0

        t = o["logical"].get("transform", "normal")
        t_str = str(t).lower().replace("_", "-")
        if t_str in ["90", "270", "flipped-90", "flipped-270"]:
            pw, ph = ph, pw

        o["logical"]["width"] = round(pw / scale)
        o["logical"]["height"] = round(ph / scale)

    def _on_mode_changed(self, name: str, modes: list, idx: int):
        if not (0 <= idx < len(modes)):
            return
        m = modes[idx]
        mode_str = f"{m.get('width', 0)}x{m.get('height', 0)}@{m.get('refresh_rate', 0) / 1000:.3f}"
        out_node = self._get_or_create_out_node(name)
        set_child_arg(out_node, "mode", mode_str)

        o = next((x for x in self._outputs if x.get("name") == name), None)
        if o:
            o["current_mode"] = idx
            self._update_logical_dims(o)

        self._commit("output mode")
        if self._canvas:
            self._canvas.queue_draw()

    def _set_output_prop(self, name: str, prop: str, value):
        if prop == "scale" and isinstance(value, float):
            value = round(value, 3)
            
        out_node = self._get_or_create_out_node(name)
        set_child_arg(out_node, prop, value)

        o = next((x for x in self._outputs if x.get("name") == name), None)
        if o:
            if "logical" not in o:
                o["logical"] = {}
            if prop == "scale":
                o["logical"]["scale"] = value
            elif prop == "transform":
                o["logical"]["transform"] = value
            self._update_logical_dims(o)

        self._commit(f"output {prop}")
        if self._canvas:
            self._canvas.queue_draw()

    def _set_output_pos(self, name: str, x: int, y: int):
        out_node = self._get_or_create_out_node(name)
        pos_node = out_node.get_child("position")
        if pos_node is None:
            pos_node = KdlNode(name="position")
            out_node.children.append(pos_node)

        pos_node.props["x"] = int(round(x))
        pos_node.props["y"] = int(round(y))

        o = next((out for out in self._outputs if out.get("name") == name), None)
        if o:
            if "logical" not in o:
                o["logical"] = {}
            o["logical"]["x"] = x
            o["logical"]["y"] = y

        self._commit("output position")
        if self._canvas:
            self._canvas.queue_draw()

    def _set_output_flag(self, name: str, flag: str, enabled: bool):
        from nirimod.kdl_parser import set_node_flag

        out_node = self._get_or_create_out_node(name)
        set_node_flag(out_node, flag, enabled)
        self._commit(f"output {flag}")
