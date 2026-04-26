"""Animations page with bezier curve editor and Nirimation preset browser."""

from __future__ import annotations

import json
import math
from pathlib import Path
import threading
import urllib.error
import urllib.request

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, GLib, Gtk

from nirimod.kdl_parser import KdlNode, find_or_create, parse_kdl, set_child_arg, set_node_flag
from nirimod.pages.base import BasePage

_NIRIMATION_API = (
    "https://api.github.com/repos/XansiVA/nirimation/contents/animations"
)
_NIRIMATION_RAW = (
    "https://raw.githubusercontent.com/XansiVA/nirimation/main/animations/{name}"
)
_NIRIMATION_HTML = (
    "https://github.com/XansiVA/nirimation/blob/main/animations/{name}"
)

# In-memory cache: None = not fetched, list = fetched entries, Exception = error
_nirimation_cache: list[dict] | Exception | None = None



ANIM_NAMES = [
    ("workspace-switch", "Workspace Switch", "video-display-symbolic"),
    ("window-open", "Window Open", "window-new-symbolic"),
    ("window-close", "Window Close", "window-close-symbolic"),
    ("window-movement", "Window Movement", "transform-move-symbolic"),
    ("window-resize", "Window Resize", "view-fullscreen-symbolic"),
    ("horizontal-view-movement", "Horizontal View Movement", "pan-end-symbolic"),
    ("config-notification-open-close", "Config Notification", "preferences-system-symbolic"),
    ("screenshot-ui-open", "Screenshot UI Open", "camera-photo-symbolic"),
    ("overview-open-close", "Overview Open/Close", "view-app-grid-symbolic"),
    ("overview-screenshot", "Overview Screenshot", "camera-photo-symbolic"),
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


def _fetch_nirimation_presets(callback):
    """Fetch preset list from nirimation GitHub API in a background thread.

    *callback* is called on the GLib main loop with either a list[dict] (success)
    or an Exception (failure). Each dict has keys: name, display_name, download_url,
    html_url.
    """
    global _nirimation_cache

    if _nirimation_cache is not None:
        result = _nirimation_cache
        GLib.idle_add(callback, result)
        return

    def _worker():
        global _nirimation_cache
        try:
            req = urllib.request.Request(
                _NIRIMATION_API,
                headers={"User-Agent": "nirimod/1.0"},
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())

            entries = []
            for item in data:
                if item.get("type") != "file":
                    continue
                n = item["name"]
                if not n.endswith(".kdl"):
                    continue
                stem = n[:-4]  # strip .kdl
                display = stem.replace("-", " ").title()
                entries.append(
                    {
                        "name": n,
                        "display_name": display,
                        "download_url": item.get(
                            "download_url",
                            _NIRIMATION_RAW.format(name=n),
                        ),
                        "html_url": item.get(
                            "html_url",
                            _NIRIMATION_HTML.format(name=n),
                        ),
                    }
                )
            entries.sort(key=lambda e: e["display_name"])
            _nirimation_cache = entries
            GLib.idle_add(callback, entries)
        except Exception as exc:
            _nirimation_cache = exc
            GLib.idle_add(callback, exc)

    threading.Thread(target=_worker, daemon=True).start()


class AnimationsPage(BasePage):
    def __init__(self, window):
        super().__init__(window)
        self._prev_anim_snapshot = None
        self._active_preset_name = None
        self._state_file = Path("~/.config/nirimod/animations.json").expanduser()
        self._load_state()

    def _load_state(self):
        try:
            if self._state_file.exists():
                with open(self._state_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._prev_anim_snapshot = data.get("prev_anim_snapshot")
                    self._active_preset_name = data.get("active_preset_name")
        except Exception as e:
            print(f"Failed to load animations state: {e}")

    def _save_state(self):
        try:
            self._state_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self._state_file, "w", encoding="utf-8") as f:
                json.dump({
                    "prev_anim_snapshot": self._prev_anim_snapshot,
                    "active_preset_name": self._active_preset_name
                }, f)
        except Exception as e:
            print(f"Failed to save animations state: {e}")

    def build(self) -> Gtk.Widget:
        tb, header, _, _ = self._make_toolbar_page("")
        header.set_title_widget(Gtk.Box()) # hide the default title

        # Custom Header (matches Workspace View / Keybindings aesthetic)
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        header_box.set_margin_start(24)
        header_box.set_margin_end(24)
        header_box.set_margin_top(20)
        header_box.set_margin_bottom(12)

        # Title/Subtitle Group
        title_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        title_vbox.set_hexpand(True)
        
        self._main_title = Gtk.Label(label="Animations")
        self._main_title.set_xalign(0.0)
        self._main_title.add_css_class("title-1")
        title_vbox.append(self._main_title)

        self._active_preset_lbl = Gtk.Label(label="Using custom animations")
        self._active_preset_lbl.set_xalign(0.0)
        self._active_preset_lbl.add_css_class("dim-label")
        self._active_preset_lbl.add_css_class("caption")
        title_vbox.append(self._active_preset_lbl)
        header_box.append(title_vbox)

        # Switch to Custom option is now inside the Custom tab


        # View Switcher (Styled as Custom/Presets buttons)
        self._view_stack = Adw.ViewStack()
        
        switcher_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        switcher_box.add_css_class("linked")
        switcher_box.set_valign(Gtk.Align.START)
        
        self._btn_custom = Gtk.ToggleButton(label="Custom")
        self._btn_presets = Gtk.ToggleButton(label="Presets")
        self._btn_presets.set_group(self._btn_custom)
        
        self._btn_custom.connect("toggled", self._on_view_toggle)
        self._btn_presets.connect("toggled", self._on_view_toggle)
        
        switcher_box.append(self._btn_custom)
        switcher_box.append(self._btn_presets)
        header_box.append(switcher_box)
        
        tb.add_top_bar(header_box)

        # Tabs
        custom_widget = self._build_custom_tab()
        self._view_stack.add_named(custom_widget, "custom")

        presets_widget = self._build_presets_tab()
        self._view_stack.add_named(presets_widget, "presets")

        # Default to Custom
        self._view_stack.set_visible_child_name("custom")
        self._btn_custom.set_active(True)

        tb.set_content(self._view_stack)

        self._update_header()
        return tb

    def _on_view_toggle(self, btn):
        if not btn.get_active():
            return
        is_custom = btn == self._btn_custom
        self._view_stack.set_visible_child_name("custom" if is_custom else "presets")

    def _update_header(self):
        if self._active_preset_name:
            self._active_preset_lbl.set_label(f"✨ Active preset: <b>{GLib.markup_escape_text(self._active_preset_name)}</b>")
            self._active_preset_lbl.set_use_markup(True)
        else:
            self._active_preset_lbl.set_label("Using custom animations")
            self._active_preset_lbl.set_use_markup(False)
        
        if hasattr(self, "_custom_switch_grp"):
            self._custom_switch_grp.set_visible(self._prev_anim_snapshot is not None)

    def _build_custom_tab(self) -> Gtk.Widget:
        """Return the custom animations tab (global toggles, bezier editor, and categories)."""
        if not hasattr(self, "_custom_scroll"):
            self._custom_scroll = Gtk.ScrolledWindow()
            self._custom_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
            self._custom_scroll.set_vexpand(True)
            self._custom_content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
            self._custom_content.set_margin_start(32)
            self._custom_content.set_margin_end(32)
            self._custom_content.set_margin_top(24)
            self._custom_content.set_margin_bottom(32)
            self._custom_scroll.set_child(self._custom_content)
        else:
            while child := self._custom_content.get_first_child():
                self._custom_content.remove(child)

        content = self._custom_content

        # Switch to Custom Banner
        self._custom_switch_grp = Adw.PreferencesGroup()
        self._custom_switch_row = Adw.ActionRow(
            title="Community Preset Active",
            subtitle="You are currently using a preset. Switch back to use your custom animation settings."
        )
        self._custom_switch_row.add_css_class("property")
        self._custom_switch_row.set_icon_name("emblem-important-symbolic")
        switch_btn = Gtk.Button(label="Switch to Custom")
        switch_btn.add_css_class("suggested-action")
        switch_btn.add_css_class("pill")
        switch_btn.set_valign(Gtk.Align.CENTER)
        switch_btn.set_margin_top(8)
        switch_btn.set_margin_bottom(8)
        switch_btn.connect("clicked", self._on_restore_previous)
        self._custom_switch_row.add_suffix(switch_btn)
        self._custom_switch_grp.add(self._custom_switch_row)
        self._custom_switch_grp.set_visible(self._prev_anim_snapshot is not None)
        content.append(self._custom_switch_grp)

        anim_node = find_or_create(self._nodes, "animations")

        # Global off toggle
        off_grp = Adw.PreferencesGroup(title="Global Settings", description="These apply to all animations universally.")
        off_row = Adw.SwitchRow(title="Enable Animations", subtitle="Toggle all desktop animations on or off")
        off_row.set_icon_name("media-playback-start-symbolic")
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
            title="Global Slowdown Factor",
            subtitle="Multiply all animation durations by this factor",
            adjustment=slowdown_adj, digits=1
        )
        slowdown_row.set_icon_name("preferences-system-time-symbolic")

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
        anim_list_grp = Adw.PreferencesGroup(title="Animation Categories", description="Configure durations and curves for specific actions.")
        for anim_key, anim_label, icon_name in ANIM_NAMES:
            row = self._build_anim_row(anim_key, anim_label, icon_name, anim_node)
            anim_list_grp.add(row)
        content.append(anim_list_grp)

        return self._custom_scroll

    def _build_presets_tab(self) -> Gtk.Widget:
        """Return the Nirimation presets tab."""
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_vexpand(True)

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        content.set_margin_start(32)
        content.set_margin_end(32)
        content.set_margin_top(24)
        content.set_margin_bottom(32)
        scroll.set_child(content)

        self._nirimation_section_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        content.append(self._nirimation_section_box)
        self._nirimation_section_box.append(self._build_nirimation_group())

        return scroll

    def _on_restore_previous(self, _btn):
        """Restore the animations block that was saved before the last preset apply."""
        if self._prev_anim_snapshot is None:
            return
        try:
            snap_nodes = parse_kdl(self._prev_anim_snapshot)
            snap_anim = next((n for n in snap_nodes if n.name == "animations"), None)
            user_nodes = self._nodes
            user_anim = next((n for n in reversed(user_nodes) if n.name == "animations"), None)
            if user_anim is None:
                user_anim = KdlNode(name="animations")
                user_anim.leading_trivia = "\n"
                user_nodes.append(user_anim)
            if snap_anim is not None:
                user_anim.children = list(snap_anim.children)
                user_anim.args = list(snap_anim.args)
                user_anim.props = dict(snap_anim.props)
            else:
                user_anim.children = []
                user_anim.args = []
                user_anim.props = {}
            self._prev_anim_snapshot = None
            self._active_preset_name = None
            self._save_state()
            self._commit("restore previous animations")
            self.show_toast("↩ Previous animations restored")
            self._update_header()
            self._build_custom_tab() # Refresh UI components
        except Exception as exc:
            self.show_toast(f"Restore failed: {exc}")

    def _build_nirimation_group(self) -> Adw.PreferencesGroup:
        """Build the Nirimation community presets section."""
        # Header: refresh button
        refresh_btn = Gtk.Button(icon_name="view-refresh-symbolic")
        refresh_btn.set_tooltip_text("Refresh preset list from GitHub")
        refresh_btn.add_css_class("flat")
        refresh_btn.add_css_class("circular")

        grp = Adw.PreferencesGroup(
            title="Nirimation Community Presets",
            description="GLSL shader animations from XansiVA/nirimation — replaces your current animations block.",
        )
        grp.set_header_suffix(refresh_btn)

        # Spinner row shown while loading
        spinner = Gtk.Spinner()
        spinner.start()
        spinner.set_margin_top(8)
        spinner.set_margin_bottom(8)

        spinner_row = Adw.ActionRow(title="Fetching presets…")
        spinner_row.add_prefix(spinner)
        grp.add(spinner_row)

        # Keep refs so callbacks can update them
        self._nirimation_grp = grp
        self._nirimation_placeholder = spinner_row
        self._nirimation_rows: list[Adw.ActionRow] = []

        def _on_result(result):
            # Remove spinner placeholder
            grp.remove(spinner_row)
            spinner.stop()

            if isinstance(result, Exception):
                err_row = Adw.ActionRow(
                    title="Unable to fetch presets",
                    subtitle=str(result),
                )
                err_row.add_prefix(
                    Gtk.Image.new_from_icon_name("network-error-symbolic")
                )
                grp.add(err_row)
                self._nirimation_rows.append(err_row)
                return

            for entry in result:
                row = self._make_nirimation_row(entry)
                grp.add(row)

        def _on_refresh_clicked(_btn):
            global _nirimation_cache
            _nirimation_cache = None  # bust cache
            # Remove all existing rows and show spinner again
            for row in list(self._nirimation_rows):
                grp.remove(row)
            self._nirimation_rows.clear()
            sp2 = Gtk.Spinner()
            sp2.start()
            sp2.set_margin_top(8)
            sp2.set_margin_bottom(8)
            wait_row = Adw.ActionRow(title="Fetching presets…")
            wait_row.add_prefix(sp2)
            grp.add(wait_row)

            def _on_result2(result):
                grp.remove(wait_row)
                sp2.stop()
                if isinstance(result, Exception):
                    err_row = Adw.ActionRow(
                        title="Unable to fetch presets",
                        subtitle=str(result),
                    )
                    err_row.add_prefix(
                        Gtk.Image.new_from_icon_name("network-error-symbolic")
                    )
                    grp.add(err_row)
                    self._nirimation_rows.append(err_row)
                    return
                for entry in result:
                    row = self._make_nirimation_row(entry)
                    grp.add(row)

            _fetch_nirimation_presets(_on_result2)

        refresh_btn.connect("clicked", _on_refresh_clicked)
        _fetch_nirimation_presets(_on_result)
        return grp

    def _make_nirimation_row(self, entry: dict) -> Adw.ActionRow:
        """Create a single preset row for the Nirimation group."""
        row = Adw.ActionRow(
            title=entry["display_name"],
            subtitle=entry["name"],
        )


        # GitHub link button
        link_btn = Gtk.Button(icon_name="web-browser-symbolic")
        link_btn.set_tooltip_text("View on GitHub")
        link_btn.add_css_class("flat")
        link_btn.add_css_class("circular")
        link_btn.set_valign(Gtk.Align.CENTER)
        link_btn.connect(
            "clicked",
            lambda _b, u=entry["html_url"]: Gtk.show_uri(None, u, 0),
        )
        row.add_suffix(link_btn)

        # Apply button
        apply_btn = Gtk.Button(label="Apply")
        apply_btn.add_css_class("suggested-action")
        apply_btn.add_css_class("pill")
        apply_btn.set_valign(Gtk.Align.CENTER)
        apply_btn.connect(
            "clicked",
            lambda _b, e=entry, r=row: self._confirm_apply_nirimation(e, r),
        )
        row.add_suffix(apply_btn)

        self._nirimation_rows.append(row)
        return row

    def _confirm_apply_nirimation(self, entry: dict, row: Adw.ActionRow):
        """Show a confirmation dialog before applying the preset."""
        try:
            dialog = Adw.AlertDialog(
                heading=f"Apply \u201c{entry['display_name']}\u201d?",
                body=(
                    "This will fully replace your current animations block with the "
                    f"\u201c{entry['display_name']}\u201d preset from XansiVA/nirimation.\n\n"
                    "Your existing bezier curves and per-animation settings will be overwritten. "
                    "You can undo this with Ctrl+Z."
                ),
            )
            dialog.add_response("cancel", "Cancel")
            dialog.add_response("apply", "Apply Preset")
            dialog.set_response_appearance("apply", Adw.ResponseAppearance.SUGGESTED)
            dialog.set_default_response("cancel")
            dialog.set_close_response("cancel")

            def _on_response(d, resp):
                if resp == "apply":
                    self._apply_nirimation_preset(entry, row)

            dialog.connect("response", _on_response)
            dialog.present(self._win)
        except AttributeError:
            # Adw.AlertDialog not available (older libadwaita) — fall back to direct apply
            self._apply_nirimation_preset(entry, row)

    def _apply_nirimation_preset(self, entry: dict, row: Adw.ActionRow):
        """Download the preset KDL and apply it (replaces the animations node)."""
        # Disable row while fetching
        row.set_sensitive(False)
        self.show_toast(f"Downloading {entry['display_name']}\u2026", timeout=5)

        def _worker():
            try:
                req = urllib.request.Request(
                    entry["download_url"],
                    headers={"User-Agent": "nirimod/1.0"},
                )
                with urllib.request.urlopen(req, timeout=10) as resp:
                    kdl_text = resp.read().decode()
                GLib.idle_add(_on_downloaded, kdl_text, None)
            except Exception as exc:
                GLib.idle_add(_on_downloaded, None, exc)

        def _on_downloaded(kdl_text, error):
            row.set_sensitive(True)
            if error:
                self.show_toast(f"Failed to download preset: {error}")
                return
            try:
                preset_nodes = parse_kdl(kdl_text)
                preset_anim = next(
                    (n for n in preset_nodes if n.name == "animations"), None
                )
                if preset_anim is None:
                    self.show_toast("Preset has no animations block — nothing applied.")
                    return

                user_nodes = self._nodes
                user_anim = next(
                    (n for n in reversed(user_nodes) if n.name == "animations"), None
                )

                # Snapshot current state BEFORE overwriting
                from nirimod.kdl_parser import write_kdl
                if user_anim is not None:
                    snap_node = KdlNode(name="animations")
                    snap_node.children = list(user_anim.children)
                    snap_node.args = list(user_anim.args)
                    snap_node.props = dict(user_anim.props)
                    self._prev_anim_snapshot = write_kdl([snap_node])
                else:
                    self._prev_anim_snapshot = write_kdl([])

                if user_anim is None:
                    user_anim = KdlNode(name="animations")
                    user_anim.leading_trivia = "\n"
                    user_nodes.append(user_anim)

                user_anim.children = list(preset_anim.children)
                user_anim.args = list(preset_anim.args)
                user_anim.props = dict(preset_anim.props)

                self._active_preset_name = entry['display_name']
                self._save_state()
                self._commit(f"nirimation preset: {entry['display_name']}")
                self._update_header()
                self.show_toast(f"\u2728 {entry['display_name']} preset applied!")
            except Exception as exc:
                self.show_toast(f"Error applying preset: {exc}")

        threading.Thread(target=_worker, daemon=True).start()

    def _apply_preset(self, curve: tuple, name: str):
        self._bezier_editor.set_curve(*curve)
        self._update_coords_label()

    def _on_bezier_changed(self, x1, y1, x2, y2):
        self._update_coords_label()

    def _update_coords_label(self):
        x1, y1, x2, y2 = self._bezier_editor.get_curve()
        self._coords_lbl.set_label(f"{x1:.3f}, {y1:.3f}, {x2:.3f}, {y2:.3f}")

    def _build_anim_row(
        self, key: str, label: str, icon_name: str, anim_node: KdlNode
    ) -> Adw.ExpanderRow:
        grp = Adw.ExpanderRow(title=label)
        grp.set_icon_name(icon_name)
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
