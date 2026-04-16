"""Outputs / Monitors page with interactive canvas."""

from __future__ import annotations

from typing import TYPE_CHECKING

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk

from nirimod import niri_ipc
from nirimod.kdl_parser import KdlNode, set_child_arg, safe_switch_connect
from nirimod.pages.base import BasePage, make_toolbar_page

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
        self._detail_groups: list[Adw.PreferencesGroup] = []
        self._canvas: Gtk.DrawingArea | None = None
        self._drag_output: str | None = None
        self._drag_offset: tuple[float, float] = (0, 0)

    def build(self) -> Gtk.Widget:
        tb, header, scroll, content = make_toolbar_page("Outputs")

        refresh_btn = Gtk.Button(icon_name="view-refresh-symbolic")
        refresh_btn.set_tooltip_text("Reload outputs from niri")
        refresh_btn.add_css_class("flat")
        refresh_btn.connect("clicked", lambda *_: self.refresh())
        header.pack_end(refresh_btn)

        canvas_frame = Gtk.Frame()
        canvas_frame.add_css_class("card")
        canvas_frame.set_margin_bottom(8)

        self._canvas = Gtk.DrawingArea()
        self._canvas.set_content_height(200)
        self._canvas.set_draw_func(self._draw_canvas)
        canvas_frame.set_child(self._canvas)
        content.append(canvas_frame)

        drag = Gtk.GestureDrag()
        drag.connect("drag-begin", self._on_drag_begin)
        drag.connect("drag-update", self._on_drag_update)
        drag.connect("drag-end", self._on_drag_end)
        self._canvas.add_controller(drag)

        self._out_combo = Adw.ComboRow(title="Monitor")
        self._out_combo.connect("notify::selected", self._on_output_selected)
        sel_group = Adw.PreferencesGroup()
        sel_group.add(self._out_combo)
        content.append(sel_group)

        self._detail_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        content.append(self._detail_box)

        self._widget = tb
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

        max_x = max_y = 1
        for o in self._outputs:
            pos = o.get("logical", {})
            px = pos.get("x", 0) + pos.get("width", 1920)
            py = pos.get("y", 0) + pos.get("height", 1080)
            max_x = max(max_x, px)
            max_y = max(max_y, py)

        scale = min((width - 40) / max_x, (height - 20) / max_y) * 0.9
        off_x = (width - max_x * scale) / 2
        off_y = (height - max_y * scale) / 2
        self._canvas_scale = scale
        self._canvas_offset = (off_x, off_y)

        for i, o in enumerate(self._outputs):
            pos = o.get("logical", {})
            x = off_x + pos.get("x", 0) * scale
            y = off_y + pos.get("y", 0) * scale
            w = pos.get("width", 1920) * scale
            h = pos.get("height", 1080) * scale

            is_sel = o.get("name") == (
                self._current_out.get("name") if self._current_out else None
            )

            cr.set_source_rgba(0, 0, 0, 0.15)
            cr.rectangle(x + 3, y + 3, w, h)
            cr.fill()

            if is_sel:
                cr.set_source_rgba(0.2, 0.5, 0.9, 0.95)
            else:
                cr.set_source_rgba(0.12, 0.12, 0.14, 0.85)
            cr.rectangle(x, y, w, h)
            cr.fill()

            cr.set_source_rgba(1, 1, 1, 0.25)
            cr.set_line_width(1.5)
            cr.rectangle(x, y, w, h)
            cr.stroke()

            name = o.get("name", f"Output {i}")
            mode_idx = o.get("current_mode")
            modes = o.get("modes", [])
            mode = (
                modes[mode_idx]
                if isinstance(mode_idx, int) and 0 <= mode_idx < len(modes)
                else {}
            )
            res = f"{mode.get('width', '?')}×{mode.get('height', '?')}"
            cr.set_source_rgba(1, 1, 1, 0.95)
            cr.select_font_face("Sans", 0, 1)
            cr.set_font_size(max(9, min(13, w / 12)))
            te = cr.text_extents(name)
            cr.move_to(x + w / 2 - te.width / 2, y + h / 2)
            cr.show_text(name)
            cr.select_font_face("Sans", 0, 0)
            cr.set_font_size(max(7, min(10, w / 16)))
            te2 = cr.text_extents(res)
            cr.move_to(x + w / 2 - te2.width / 2, y + h / 2 + 14)
            cr.show_text(res)

    def _on_drag_begin(self, gesture, sx, sy):
        if not hasattr(self, "_canvas_scale"):
            return
        scale = self._canvas_scale
        ox, oy = self._canvas_offset
        for o in self._outputs:
            pos = o.get("logical", {})
            x = ox + pos.get("x", 0) * scale
            y = oy + pos.get("y", 0) * scale
            w = pos.get("width", 1920) * scale
            h = pos.get("height", 1080) * scale
            if x <= sx <= x + w and y <= sy <= y + h:
                self._drag_output = o["name"]
                self._drag_start_pos = (pos.get("x", 0), pos.get("y", 0))
                self._drag_offset = (sx - x, sy - y)
                return

    def _on_drag_update(self, gesture, dx, dy):
        if not self._drag_output or not hasattr(self, "_canvas_scale"):
            return
        start_x, start_y = gesture.get_start_point()[1], gesture.get_start_point()[2]
        scale = self._canvas_scale
        ox, oy = self._canvas_offset
        new_lx = round((start_x + dx - ox - self._drag_offset[0]) / scale / 10) * 10
        new_ly = round((start_y + dy - oy - self._drag_offset[1]) / scale / 10) * 10
        for o in self._outputs:
            if o["name"] == self._drag_output:
                if "logical" not in o:
                    o["logical"] = {}
                o["logical"]["x"] = max(0, new_lx)
                o["logical"]["y"] = max(0, new_ly)
        if self._canvas:
            self._canvas.queue_draw()

    def _on_drag_end(self, gesture, dx, dy):
        if self._drag_output:
            self._apply_position(self._drag_output)
            self._drag_output = None

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
        pos_node.props["x"] = pos.get("x", 0)
        pos_node.props["y"] = pos.get("y", 0)

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

        scale_adj = Gtk.Adjustment(
            value=output.get("logical", {}).get("scale", 1.0),
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
        if out_node is None:
            out_node = KdlNode(name="output", args=[name])
            nodes.append(out_node)
        self._ensure_output_fields(out_node, name)

        # Ensure the specified order in nirimod.kdl output block
        order = {"mode": 0, "scale": 1, "transform": 2, "position": 3}
        out_node.children.sort(key=lambda c: order.get(c.name, 999))

        return out_node

    def _on_mode_changed(self, name: str, modes: list, idx: int):
        if not (0 <= idx < len(modes)):
            return
        m = modes[idx]
        mode_str = f"{m.get('width', 0)}x{m.get('height', 0)}@{m.get('refresh_rate', 0) / 1000:.3f}"
        out_node = self._get_or_create_out_node(name)
        set_child_arg(out_node, "mode", mode_str)
        self._commit("output mode")

    def _set_output_prop(self, name: str, prop: str, value):
        out_node = self._get_or_create_out_node(name)
        set_child_arg(out_node, prop, value)
        self._commit(f"output {prop}")

    def _set_output_pos(self, name: str, x: int, y: int):
        out_node = self._get_or_create_out_node(name)
        pos_node = out_node.get_child("position")
        if pos_node is None:
            pos_node = KdlNode(name="position")
            out_node.children.append(pos_node)
        pos_node.props["x"] = x
        pos_node.props["y"] = y
        self._commit("output position")
        if self._canvas:
            self._canvas.queue_draw()

    def _set_output_flag(self, name: str, flag: str, enabled: bool):
        from nirimod.kdl_parser import set_node_flag

        out_node = self._get_or_create_out_node(name)
        set_node_flag(out_node, flag, enabled)
        self._commit(f"output {flag}")
