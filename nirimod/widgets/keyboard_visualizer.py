"""Keyboard visualizer widget — Cairo DrawingArea keyboard map.

Ported from omer-biz/visu (Elm/WASM) into pure Python + Cairo.
The layout mirrors visu's `keyboardLayout` list exactly (56-key ANSI QWERTY).
"""

from __future__ import annotations

import math

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, GLib, GObject, Gtk

from nirimod.xkb_helper import XkbHelper

# Geometry data: (key_id, width_units)
# Rows total 60 units each.
KEYBOARD_GEOMETRIES: dict[str, list[list[tuple[str, int]]]] = {
    "ANSI": [
        # Row 1 — number row
        [("escape", 4), ("1", 4), ("2", 4), ("3", 4), ("4", 4), ("5", 4), ("6", 4), ("7", 4), ("8", 4), ("9", 4), ("0", 4), ("minus", 4), ("equal", 4), ("backspace", 8)],
        # Row 2 — QWERTY
        [("tab", 6), ("q", 4), ("w", 4), ("e", 4), ("r", 4), ("t", 4), ("y", 4), ("u", 4), ("i", 4), ("o", 4), ("p", 4), ("bracketleft", 4), ("bracketright", 4), ("backslash", 6)],
        # Row 3 — home row
        [("capslock", 7), ("a", 4), ("s", 4), ("d", 4), ("f", 4), ("g", 4), ("h", 4), ("j", 4), ("k", 4), ("l", 4), ("semicolon", 4), ("quote", 4), ("return", 9)],
        # Row 4 — shift row
        [("shiftleft", 7), ("z", 4), ("x", 4), ("c", 4), ("v", 4), ("b", 4), ("n", 4), ("m", 4), ("comma", 4), ("period", 4), ("slash", 4), ("shiftright", 5), ("up", 4), ("", 4)],
        # Row 5 — bottom row
        [("ctrlleft", 6), ("superleft", 6), ("altleft", 6), ("space", 24), ("altright", 6), ("left", 4), ("down", 4), ("right", 4)],
    ],
    "ISO": [
        # Row 1 — number row
        [("escape", 4), ("grave", 4), ("1", 4), ("2", 4), ("3", 4), ("4", 4), ("5", 4), ("6", 4), ("7", 4), ("8", 4), ("9", 4), ("0", 4), ("minus", 4), ("equal", 4), ("backspace", 4)],
        # Row 2 — QWERTY
        [("tab", 6), ("q", 4), ("w", 4), ("e", 4), ("r", 4), ("t", 4), ("y", 4), ("u", 4), ("i", 4), ("o", 4), ("p", 4), ("bracketleft", 4), ("bracketright", 4), ("return", 6)],
        # Row 3 — home row
        [("capslock", 7), ("a", 4), ("s", 4), ("d", 4), ("f", 4), ("g", 4), ("h", 4), ("j", 4), ("k", 4), ("l", 4), ("semicolon", 4), ("quote", 4), ("backslash", 4), ("return", 5)],
        # Row 4 — shift row
        [("shiftleft", 4), ("less", 4), ("z", 4), ("x", 4), ("c", 4), ("v", 4), ("b", 4), ("n", 4), ("m", 4), ("comma", 4), ("period", 4), ("slash", 4), ("shiftright", 4), ("up", 4), ("", 4)],
        # Row 5 — bottom row
        [("ctrlleft", 6), ("superleft", 6), ("altleft", 6), ("space", 24), ("altright", 6), ("left", 4), ("down", 4), ("right", 4)],
    ]
}

_KID_TO_KEYCODE = {
    # Row 1
    "escape": 1, "grave": 41, "1": 2, "2": 3, "3": 4, "4": 5, "5": 6, "6": 7, "7": 8, "8": 9, "9": 10, "0": 11, "minus": 12, "equal": 13, "backspace": 14,
    # Row 2
    "tab": 15, "q": 16, "w": 17, "e": 18, "r": 19, "t": 20, "y": 21, "u": 22, "i": 23, "o": 24, "p": 25, "bracketleft": 26, "bracketright": 27, "backslash": 43,
    # Row 3
    "capslock": 58, "a": 30, "s": 31, "d": 32, "f": 33, "g": 34, "h": 35, "j": 36, "k": 37, "l": 38, "semicolon": 39, "quote": 40, "return": 28,
    # Row 4
    "shiftleft": 42, "less": 94, "z": 44, "x": 45, "c": 46, "v": 47, "b": 48, "n": 49, "m": 50, "comma": 51, "period": 52, "slash": 53, "shiftright": 54, "up": 103,
    # Row 5
    "ctrlleft": 29, "superleft": 125, "altleft": 56, "space": 57, "altright": 100, "left": 105, "down": 108, "right": 106
}

# Static fallbacks for modifiers and special keys
_STATIC_LABELS = {
    "escape": "Esc", "backspace": "Bksp", "tab": "Tab", "return": "Enter", "capslock": "Caps",
    "shiftleft": "Shift", "shiftright": "Shift", "ctrlleft": "Ctrl", "superleft": "Super",
    "altleft": "Alt", "altright": "Alt", "up": "↑", "down": "↓", "left": "←", "right": "→", "space": ""
}


_MODIFIER_KEY_IDS = {
    "shiftleft",
    "shiftright",
    "ctrlleft",
    "altleft",
    "altright",
    "superleft",
    "capslock",
    "tab",
    "backspace",
    "space",
}

# Niri keysym → keyboard id normalisation table

_KEYSYM_ALIAS: dict[str, str] = {
    "return": "return",
    "enter": "return",
    "kp_enter": "return",
    "escape": "escape",
    "esc": "escape",
    "backspace": "backspace",
    "tab": "tab",
    "space": "space",
    "bracketleft": "bracketleft",
    "bracketright": "bracketright",
    "minus": "minus",
    "equal": "equal",
    "period": "period",
    "comma": "comma",
    "slash": "slash",
    "backslash": "backslash",
    "semicolon": "semicolon",
    "apostrophe": "quote",
    "quote": "quote",
    "grave": "grave",
    "up": "up",
    "down": "down",
    "left": "left",
    "right": "right",
    "page_up": "pageup",
    "page_down": "pagedown",
    "home": "home",
    "end": "end",
    "print": "print",
    "delete": "delete",
    "insert": "insert",
}

for _c in "abcdefghijklmnopqrstuvwxyz0123456789":
    _KEYSYM_ALIAS[_c] = _c


def normalize_key_id(raw_key: str) -> str:
    """Convert a raw keysym (last part of Mod+Shift+X) to a keyboard layout id."""
    k = raw_key.strip().lower()
    return _KEYSYM_ALIAS.get(k, k)


# Colour palette (matches NiriMod dark theme)
def _rgb(r: int, g: int, b: int, a: float = 1.0):
    return (r / 255, g / 255, b / 255, a)


_COL_KEY_BG = _rgb(24, 24, 27)
_COL_KEY_BORDER = _rgb(255, 255, 255, 0.06)
_COL_KEY_FG = _rgb(161, 161, 170)

_COL_BOUND_BG = _rgb(88, 28, 135, 0.45)
_COL_BOUND_BORDER = _rgb(147, 51, 234, 0.7)
_COL_BOUND_MOD = _rgb(192, 132, 252)

_COL_SEL_BG = _rgb(126, 34, 206, 0.6)
_COL_SEL_BORDER = _rgb(168, 85, 247, 1.0)

_COL_SEARCH_BG = _rgb(192, 97, 203, 0.35)
_COL_SEARCH_BORDER = _rgb(192, 97, 203, 1.0)

_COL_FRAME_BG = _rgb(12, 12, 13)
_COL_FRAME_BORDER = _rgb(255, 255, 255, 0.08)


class KeyboardVisualizer(Gtk.Box):
    """Cairo-rendered ANSI QWERTY keyboard with niri binding overlays."""

    __gsignals__ = {
        "key-selected": (GObject.SignalFlags.RUN_FIRST, None, (str,)),
        "edit-binding": (GObject.SignalFlags.RUN_FIRST, None, (object,)),
        "add-binding": (GObject.SignalFlags.RUN_FIRST, None, (str,)),
    }

    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12)

        # State
        self._layout_id: str = "us"
        self._geometry_id: str = "ANSI"
        self._bindings: dict[str, list[dict]] = {}  # key_id → [bind_dict, ...]
        self._selected_id: str | None = None
        self._search_q: str = ""
        self._dynamic_keysym_to_kid: dict[str, str] = {}
        
        self._xkb = XkbHelper()
        self._xkb.set_layout(self._layout_id)

        # Precompute flat list for hit-tests
        self._key_rects: list[tuple[str, float, float, float, float]] = []
        # (key_id, x, y, w, h) — populated on first draw

        # Drawing area
        self._area = Gtk.DrawingArea()
        self._area.set_hexpand(True)
        self._area.set_draw_func(self._draw)


        self._aspect_frame = Gtk.AspectFrame(ratio=2.8, obey_child=False)
        self._aspect_frame.set_child(self._area)
        self.append(self._aspect_frame)

        click = Gtk.GestureClick()
        click.connect("released", self._on_click)
        self._area.add_controller(click)



        # Action overlay panel
        self._panel = _ActionPanel(
            on_edit=lambda b: self.emit("edit-binding", b),
            on_add=lambda k: self.emit("add-binding", k),
        )
        self.append(self._panel)

        # Legend
        self.append(self._build_legend())

    # Public API

    def set_bindings(self, bindings: dict[str, list[dict]]) -> None:
        """Accept a key_id → [bind_dict] mapping and refresh."""
        self._bindings = bindings
        self._area.queue_draw()
        # Refresh panel if a key was already selected
        if self._selected_id:
            self._panel.update(
                self._selected_id, self._bindings.get(self._selected_id, [])
            )

    def set_layout(self, layout_id: str) -> None:
        """Set the visualizer layout mapping (e.g. 'us', 'it')."""
        self._layout_id = layout_id
        self._xkb.set_layout(layout_id)
        

        base_layout = layout_id.split(":")[0].lower()
        iso_layouts = {'it', 'fr', 'de', 'es', 'pt', 'uk', 'ru', 'ch', 'be', 'no', 'se', 'fi', 'dk'}
        if base_layout in iso_layouts:
            self._geometry_id = "ISO"
        else:
            self._geometry_id = "ANSI"
            
        self._dynamic_keysym_to_kid.clear()
        for kid, keycode in _KID_TO_KEYCODE.items():
            sym = self._xkb.get_keysym_name(keycode)
            if sym:
                self._dynamic_keysym_to_kid[sym.lower()] = kid
            
        self._area.queue_draw()

    def set_search(self, query: str) -> None:
        self._search_q = query.strip().lower()
        self._area.queue_draw()

    def clear_selection(self) -> None:
        self._selected_id = None
        self._panel.clear()
        self._area.queue_draw()

    # Internal helpers

    def _on_click(self, gesture, n_press, x, y):
        for kid, rx, ry, rw, rh in self._key_rects:
            if rx <= x <= rx + rw and ry <= y <= ry + rh:
                self._selected_id = kid
                self._panel.update(kid, self._bindings.get(kid, []))
                self._area.queue_draw()
                self.emit("key-selected", kid)
                return

    def _matches_search(self, binds: list[dict]) -> bool:
        if not self._search_q:
            return False
        q = self._search_q
        for b in binds:
            if q in b.get("action", "").lower():
                return True
            if q in b.get("keysym", "").lower():
                return True
        return False

    def _draw(self, area, cr, width: int, height: int):
        self._key_rects = []

        # Margins for the outer "chassis"
        chassis_pad = 12
        pad_x, pad_y = 20, 16  # padding inside the chassis

        inner_w = width - 2 * pad_x
        inner_h = height - 2 * pad_y

        active_geom = KEYBOARD_GEOMETRIES.get(self._geometry_id) or KEYBOARD_GEOMETRIES["ANSI"]
        n_rows = len(active_geom)
        row_h = inner_h / n_rows
        key_gap = max(4.0, row_h * 0.12)
        radius = max(4.0, row_h * 0.18)

        # 1. Draw the Keyboard Chassis
        cr.set_source_rgba(*_COL_FRAME_BG)
        self._rounded_rect(cr, chassis_pad, chassis_pad, width - 2 * chassis_pad, height - 2 * chassis_pad, radius * 1.5)
        cr.fill_preserve()
        cr.set_source_rgba(*_COL_FRAME_BORDER)
        cr.set_line_width(1.5)
        cr.stroke()

        # Compute max row width from actual layout data (rows are all equal)
        total_units = max(sum(w for _, w in row) for row in active_geom)

        for row_idx, row in enumerate(active_geom):
            y = float(pad_y + row_idx * row_h)
            x = float(pad_x)

            for kid, units in row:
                key_w = (units / total_units) * inner_w

                # Spacer key — advance x but draw nothing
                if not kid:
                    x += key_w
                    continue
                
                # Fetch dynamic label
                label = _STATIC_LABELS.get(kid)
                if label is None:
                    keycode = _KID_TO_KEYCODE.get(kid)
                    if keycode:
                        label = self._xkb.get_label(keycode)
                
                if label is None:
                    label = kid.upper() if len(kid) <= 1 else kid.capitalize()
                else:
                    label = label.upper() if len(label) == 1 else label
                key_rect_x = x + key_gap / 2
                key_rect_y = y + key_gap / 2
                key_rect_w = key_w - key_gap
                key_rect_h = row_h - key_gap

                # Determine state
                binds = self._bindings.get(kid, [])
                is_bound = bool(binds)
                is_sel = self._selected_id == kid
                is_search = is_bound and self._matches_search(binds)

                # Choose colours
                if is_sel:
                    bg, border = _COL_SEL_BG, _COL_SEL_BORDER
                    lw = 2.0
                elif is_search:
                    bg, border = _COL_SEARCH_BG, _COL_SEARCH_BORDER
                    lw = 1.8
                elif is_bound:
                    bg, border = _COL_BOUND_BG, _COL_BOUND_BORDER
                    lw = 1.4
                else:
                    bg, border = _COL_KEY_BG, _COL_KEY_BORDER
                    lw = 1.0

                # Draw Key Shadow/Depth (solid color at bottom)
                cr.set_source_rgba(0, 0, 0, 0.3)
                self._rounded_rect(
                    cr, key_rect_x, key_rect_y + 1, key_rect_w, key_rect_h, radius
                )
                cr.fill()

                # Draw Key Body
                self._rounded_rect(
                    cr, key_rect_x, key_rect_y, key_rect_w, key_rect_h, radius
                )
                cr.set_source_rgba(*bg)
                cr.fill_preserve()
                cr.set_source_rgba(*border)
                cr.set_line_width(lw)
                cr.stroke()

                # Selected glow ring
                if is_sel:
                    cr.set_source_rgba(168 / 255, 85 / 255, 247 / 255, 0.15)
                    cr.set_line_width(5.0)
                    self._rounded_rect(
                        cr,
                        key_rect_x - 3,
                        key_rect_y - 3,
                        key_rect_w + 6,
                        key_rect_h + 6,
                        radius + 3,
                    )
                    cr.stroke()

                # Modifier badge (top-left tiny text)
                if is_bound and not is_sel:
                    first_mod = self._first_modifier(binds)
                    if first_mod:
                        cr.set_source_rgba(*_COL_BOUND_MOD)
                        cr.select_font_face(
                            "Inter",
                            0,  # SLANT_NORMAL
                            1,
                        )  # WEIGHT_BOLD
                        badge_fs = max(6.5, key_rect_h * 0.18)
                        cr.set_font_size(badge_fs)
                        cr.move_to(key_rect_x + 4, key_rect_y + badge_fs + 2)
                        cr.show_text(first_mod[:4].upper())

                fs = max(8.0, key_rect_h * 0.32)
                cr.set_font_size(fs)
                cr.select_font_face("Inter", 0, 1)

                if is_bound:
                    cr.set_source_rgba(0.95, 0.95, 1, 1.0)
                else:
                    cr.set_source_rgba(*_COL_KEY_FG)

                te = cr.text_extents(label)
                tx = key_rect_x + (key_rect_w - te.width) / 2 - te.x_bearing
                ty = key_rect_y + (key_rect_h + te.height) / 2 - te.height / 2
                cr.move_to(tx, ty)
                cr.show_text(label)

                # Binding count badge (bottom-right)
                if len(binds) > 1:
                    badge_txt = str(len(binds))
                    bfs = max(6.0, key_rect_h * 0.16)
                    cr.set_font_size(bfs)
                    bte = cr.text_extents(badge_txt)
                    bpad = 3.0
                    bw = bte.width + bpad * 2
                    bh = bte.height + bpad * 2
                    bx = key_rect_x + key_rect_w - bw - 4
                    by = key_rect_y + key_rect_h - bh - 4
                    # Badge background circle
                    cr.set_source_rgba(*_COL_SEL_BORDER)
                    self._rounded_rect(cr, bx, by, bw, bh, bh / 2)
                    cr.fill()
                    cr.set_source_rgba(1, 1, 1)
                    cr.move_to(bx + bpad - bte.x_bearing, by + bpad - bte.y_bearing)
                    cr.show_text(badge_txt)

                # Store hit-test rect
                self._key_rects.append(
                    (kid, key_rect_x, key_rect_y, key_rect_w, key_rect_h)
                )
                x += key_w

    @staticmethod
    def _rounded_rect(cr, x: float, y: float, w: float, h: float, r: float):
        r = min(r, w / 2, h / 2)
        cr.new_sub_path()
        cr.arc(x + w - r, y + r, r, -math.pi / 2, 0)
        cr.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
        cr.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
        cr.arc(x + r, y + r, r, math.pi, 3 * math.pi / 2)
        cr.close_path()

    @staticmethod
    def _first_modifier(binds: list[dict]) -> str:
        if not binds:
            return ""
        keysym = binds[0].get("keysym", "")
        parts = keysym.split("+")
        if len(parts) > 1:
            m = parts[0].lower()
            _mod_labels = {
                "mod": "MOD",
                "super": "SUP",
                "ctrl": "CTL",
                "control": "CTL",
                "shift": "SHF",
                "alt": "ALT",
                "win": "WIN",
            }
            return _mod_labels.get(m, m[:4].upper())
        return ""

    @staticmethod
    def _build_legend() -> Gtk.Box:
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=20)
        box.set_halign(Gtk.Align.CENTER)
        box.set_margin_top(2)
        box.set_opacity(0.65)

        def _chip(rgba_css: str, text: str) -> Gtk.Box:
            hb = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            swatch = Gtk.Box()
            swatch.set_size_request(12, 12)
            swatch.add_css_class("nm-kb-swatch")

            attrs = Gtk.CssProvider()
            attrs.load_from_data(
                f".nm-kb-swatch {{ background: {rgba_css}; border-radius: 3px; }}".encode()
            )
            swatch.get_style_context().add_provider(
                attrs, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
            )
            lbl = Gtk.Label(label=text)
            lbl.add_css_class("caption")
            hb.append(swatch)
            hb.append(lbl)
            return hb

        box.append(_chip("rgba(147, 51, 234, 0.7)", "Bound"))
        box.append(_chip("rgba(192, 97, 203, 1.0)", "Search match"))
        box.append(_chip("rgba(168, 85, 247, 1.0)", "Selected"))
        box.append(_chip("rgba(24, 24, 27, 1.0)", "Unbound"))
        return box


# Action overlay panel


class _ActionPanel(Gtk.Box):
    """Shows the binding details for the currently selected key."""

    def __init__(self, on_edit=None, on_add=None):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self._on_edit = on_edit
        self._on_add = on_add
        self.add_css_class("nm-kb-action-panel")
        self.set_visible(False)

        # Header row
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        header.set_margin_start(14)
        header.set_margin_end(14)
        header.set_margin_top(10)
        header.set_margin_bottom(6)

        self._key_label = Gtk.Label(label="")
        self._key_label.add_css_class("nm-kb-key-id-label")
        self._key_label.set_xalign(0.0)
        self._key_label.set_hexpand(True)
        header.append(self._key_label)

        self._count_label = Gtk.Label(label="")
        self._count_label.add_css_class("dim-label")
        self._count_label.add_css_class("caption")
        header.append(self._count_label)
        self.append(header)

        self.append(Gtk.Separator())


        self._grp_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self._grp_container.set_margin_start(8)
        self._grp_container.set_margin_end(8)
        self._grp_container.set_margin_top(6)
        self._grp_container.set_margin_bottom(8)
        self.append(self._grp_container)

        # def clear(self):
        self.set_visible(False)

    def update(self, key_id: str, binds: list[dict]):
        # Clear previous group from the container
        while True:
            c = self._grp_container.get_first_child()
            if c is None:
                break
            self._grp_container.remove(c)

        new_grp = Adw.PreferencesGroup()

        if not binds:
            self._key_label.set_label(key_id.upper())
            self._count_label.set_label("No bindings")
            
            add_btn = Gtk.Button(label=f"Create Binding for {key_id.upper()}")
            add_btn.add_css_class("suggested-action")
            add_btn.add_css_class("pill")
            add_btn.set_halign(Gtk.Align.CENTER)
            add_btn.set_margin_top(8)
            add_btn.set_margin_bottom(8)
            if self._on_add:
                add_btn.connect("clicked", lambda *_: self._on_add(key_id))
            
            new_grp.add(add_btn)
        else:
            self._key_label.set_label(key_id.upper())
            n = len(binds)
            self._count_label.set_label(f"{n} binding" + ("s" if n != 1 else ""))
            for b in binds:
                keysym = b.get("keysym", "?")
                action = b.get("action", "")
                args = b.get("action_args") or []
                arg_str = " ".join(str(a) for a in args)
                full_action = f"{action} {arg_str}".strip() or "(no action)"

                row = Adw.ActionRow(title=GLib.markup_escape_text(full_action))

                # Keycap Prefix
                keys_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
                keys_box.set_valign(Gtk.Align.CENTER)
                keys_box.set_margin_start(4)
                keys_box.set_margin_end(16)

                parts = keysym.split("+")
                _labels = {
                    "mod": "Mod",
                    "super": "Super",
                    "ctrl": "Ctrl",
                    "control": "Ctrl",
                    "shift": "Shift",
                    "alt": "Alt",
                    "win": "Win",
                }

                for i, part in enumerate(parts):
                    label_text = part
                    is_mod = i < len(parts) - 1
                    if is_mod:
                        label_text = _labels.get(part.lower(), part)
                    else:
                        label_text = (
                            label_text.upper() if len(label_text) == 1 else label_text
                        )

                    cap = Gtk.Label(label=label_text)
                    if is_mod:
                        cap.add_css_class("nm-keycap-mod")
                    else:
                        cap.add_css_class("nm-keycap-main")
                    keys_box.append(cap)

                row.add_prefix(keys_box)

                # Lock badge
                if b.get("allow_when_locked"):
                    lock = Gtk.Label(label="🔒")
                    lock.set_tooltip_text("Allowed when screen is locked")
                    lock.set_valign(Gtk.Align.CENTER)
                    row.add_suffix(lock)
                    
                # Edit Button
                edit_btn = Gtk.Button(icon_name="document-edit-symbolic")
                edit_btn.add_css_class("flat")
                edit_btn.add_css_class("circular")
                edit_btn.set_valign(Gtk.Align.CENTER)
                if self._on_edit:
                    edit_btn.connect("clicked", lambda *_, bind_ref=b: self._on_edit(bind_ref))
                row.add_suffix(edit_btn)

                new_grp.add(row)

        self._grp_container.append(new_grp)
        self.set_visible(True)


def _extract_modifiers(keysym: str) -> list[str]:
    parts = keysym.split("+")
    result = []
    _labels = {
        "mod": "Mod",
        "super": "Super",
        "ctrl": "Ctrl",
        "control": "Ctrl",
        "shift": "Shift",
        "alt": "Alt",
        "win": "Win",
    }
    for p in parts[:-1]:
        result.append(_labels.get(p.lower(), p))
    return result
