"""Keyboard visualizer widget — Cairo DrawingArea keyboard map.

Inspired from omer-biz/visu (Elm/WASM) into pure Python + Cairo.
"""

from __future__ import annotations

import math

try:
    import cairo  # noqa: F401
    HAS_CAIRO = True
except ImportError:
    HAS_CAIRO = False

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, GLib, GObject, Gtk

from nirimod.xkb_helper import XkbHelper

KEYBOARD_GEOMETRIES: dict[str, list[list[tuple[str, int]]]] = {
    "ANSI": [
        # Row 0 — function row
        [("escape", 4), ("", 2), ("f1", 3), ("f2", 3), ("f3", 3), ("f4", 3), ("", 2), ("f5", 3), ("f6", 3), ("f7", 3), ("f8", 3), ("", 2), ("f9", 3), ("f10", 3), ("f11", 3), ("f12", 3), ("", 2), ("print", 4), ("insert", 4), ("delete", 4)],
        # Row 1 — number row
        [("grave", 4), ("1", 4), ("2", 4), ("3", 4), ("4", 4), ("5", 4), ("6", 4), ("7", 4), ("8", 4), ("9", 4), ("0", 4), ("minus", 4), ("equal", 4), ("backspace", 8)],
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
        # Row 0 — function row
        [("escape", 4), ("", 2), ("f1", 3), ("f2", 3), ("f3", 3), ("f4", 3), ("", 2), ("f5", 3), ("f6", 3), ("f7", 3), ("f8", 3), ("", 2), ("f9", 3), ("f10", 3), ("f11", 3), ("f12", 3), ("", 2), ("print", 4), ("insert", 4), ("delete", 4)],
        # Row 1 — number row
        [("grave", 4), ("1", 4), ("2", 4), ("3", 4), ("4", 4), ("5", 4), ("6", 4), ("7", 4), ("8", 4), ("9", 4), ("0", 4), ("minus", 4), ("equal", 4), ("backspace", 8)],
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
    # Function row
    "escape": 1, "f1": 59, "f2": 60, "f3": 61, "f4": 62, "f5": 63, "f6": 64, "f7": 65, "f8": 66, "f9": 67, "f10": 68, "f11": 87, "f12": 88, "print": 99, "insert": 110, "delete": 111,
    # Number row
    "grave": 41, "1": 2, "2": 3, "3": 4, "4": 5, "5": 6, "6": 7, "7": 8, "8": 9, "9": 10, "0": 11, "minus": 12, "equal": 13, "backspace": 14,
    # Row 2
    "tab": 15, "q": 16, "w": 17, "e": 18, "r": 19, "t": 20, "y": 21, "u": 22, "i": 23, "o": 24, "p": 25, "bracketleft": 26, "bracketright": 27, "backslash": 43,
    # Row 3
    "capslock": 58, "a": 30, "s": 31, "d": 32, "f": 33, "g": 34, "h": 35, "j": 36, "k": 37, "l": 38, "semicolon": 39, "quote": 40, "return": 28,
    # Row 4
    "shiftleft": 42, "less": 94, "z": 44, "x": 45, "c": 46, "v": 47, "b": 48, "n": 49, "m": 50, "comma": 51, "period": 52, "slash": 53, "shiftright": 54, "up": 103,
    # Row 5
    "ctrlleft": 29, "superleft": 125, "altleft": 56, "space": 57, "altright": 100, "left": 105, "down": 108, "right": 106
}

_STATIC_LABELS = {
    "escape": "Esc", "backspace": "Bksp", "tab": "Tab", "return": "Enter", "capslock": "Caps",
    "shiftleft": "Shift", "shiftright": "Shift", "ctrlleft": "Ctrl", "superleft": "Super",
    "altleft": "Alt", "altright": "Alt", "up": "↑", "down": "↓", "left": "←", "right": "→", "space": "",
    "grave": "`",
    "f1": "F1", "f2": "F2", "f3": "F3", "f4": "F4", "f5": "F5", "f6": "F6",
    "f7": "F7", "f8": "F8", "f9": "F9", "f10": "F10", "f11": "F11", "f12": "F12",
    "print": "PrtSc", "insert": "Ins", "delete": "Del",
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
    "sysrq": "print",
    "delete": "delete",
    "del": "delete",
    "insert": "insert",
    "ins": "insert",
    "f1": "f1", "f2": "f2", "f3": "f3", "f4": "f4",
    "f5": "f5", "f6": "f6", "f7": "f7", "f8": "f8",
    "f9": "f9", "f10": "f10", "f11": "f11", "f12": "f12",
}

for _c in "abcdefghijklmnopqrstuvwxyz0123456789":
    _KEYSYM_ALIAS[_c] = _c


def normalize_key_id(raw_key: str) -> str:
    """Convert a raw keysym (last part of Mod+Shift+X) to a keyboard layout id."""
    k = raw_key.strip().lower()
    return _KEYSYM_ALIAS.get(k, k)


def _rgb(r: int, g: int, b: int, a: float = 1.0):
    return (r / 255, g / 255, b / 255, a)


# Unbound key
_COL_KEY_BG       = _rgb(30, 30, 36)          # dark charcoal fill
_COL_KEY_BORDER   = _rgb(255, 255, 255, 0.07) # barely visible edge
_COL_KEY_FG       = _rgb(200, 200, 210)        # label colour

# Bound key
_COL_BOUND_BG     = _rgb(45, 30, 80)           # muted indigo fill
_COL_BOUND_BORDER = _rgb(100, 60, 160, 1.0)    # soft purple border
_COL_BOUND_GLOW   = _rgb(100, 60, 160, 0.20)   # subtle outer glow
_COL_BOUND_MOD    = _rgb(160, 140, 200)         # muted MOD label tint

# Selected key
_COL_SEL_BG       = _rgb(70, 40, 120)
_COL_SEL_BORDER   = _rgb(140, 80, 200, 1.0)
_COL_SEL_GLOW     = _rgb(140, 80, 200, 0.30)

# Search-match key
_COL_SEARCH_BG     = _rgb(100, 50, 130)
_COL_SEARCH_BORDER = _rgb(160, 80, 180, 1.0)
_COL_SEARCH_GLOW   = _rgb(160, 80, 180, 0.25)

# Badge pill
_COL_BADGE_BG   = _rgb(80, 40, 140)
_COL_BADGE_FG   = _rgb(255, 255, 255)

# Chassis
_COL_FRAME_BG     = _rgb(10, 10, 12)
_COL_FRAME_BORDER = _rgb(255, 255, 255, 0.07)


class _AspectDrawingArea(Gtk.DrawingArea):
    def __init__(self, ratio=2.43):
        super().__init__()
        self._ratio = ratio
        self.set_hexpand(True)

    def do_get_request_mode(self):
        return Gtk.SizeRequestMode.HEIGHT_FOR_WIDTH

    def do_measure(self, orientation, for_size):
        if orientation == Gtk.Orientation.HORIZONTAL:
            return (400, 560, -1, -1)
        else:
            if for_size > 0:
                h = int(for_size / self._ratio)
                return (h, h, -1, -1)
            else:
                h = int(560 / self._ratio)
                return (h, h, -1, -1)


class KeyboardVisualizer(Gtk.Box):
    """Cairo-rendered ANSI QWERTY keyboard with niri binding overlays."""

    __gsignals__ = {
        "key-selected": (GObject.SignalFlags.RUN_FIRST, None, (str,)),
        "edit-binding": (GObject.SignalFlags.RUN_FIRST, None, (object,)),
        "add-binding": (GObject.SignalFlags.RUN_FIRST, None, (str,)),
        "delete-binding": (GObject.SignalFlags.RUN_FIRST, None, (object,)),
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

        self._key_rects: list[tuple[str, float, float, float, float]] = []

        if not HAS_CAIRO:
            err_lbl = Gtk.Label(
                label="Cairo is not installed — the physical keyboard view is unavailable.\nInstall dev-python/pycairo and restart.",
                justify=Gtk.Justification.CENTER,
            )
            err_lbl.add_css_class("dim-label")
            err_lbl.set_vexpand(True)
            self.append(err_lbl)
            return

        # Drawing area
        self._area = _AspectDrawingArea(ratio=2.43)
        self._area.set_draw_func(self._draw)
        self.append(self._area)

        click = Gtk.GestureClick()
        click.connect("released", self._on_click)
        self._area.add_controller(click)

        if HAS_CAIRO:
            self._panel = _ActionPanel(
                on_edit=lambda b: self.emit("edit-binding", b),
                on_add=lambda k: self.emit("add-binding", k),
                on_delete=lambda b: self.emit("delete-binding", b),
            )
            self.append(self._panel)

            # Legend
            self.append(self._build_legend())

    # Public API

    def set_bindings(self, bindings: dict[str, list[dict]]) -> None:
        """Accept a key_id → [bind_dict] mapping and refresh."""
        self._bindings = bindings
        if hasattr(self, "_area"):
            self._area.queue_draw()
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
            
        if hasattr(self, "_area"):
            self._area.queue_draw()

    def set_search(self, query: str) -> None:
        self._search_q = query.strip().lower()
        if hasattr(self, "_area"):
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
        if width <= 0 or height <= 0:
            return
        self._key_rects = []

        # Internal margins
        pad_x, pad_y = 16, 12
        chassis_r = 12.0

        inner_w = width - 2 * pad_x
        inner_h = height - 2 * pad_y

        active_geom = KEYBOARD_GEOMETRIES.get(self._geometry_id) or KEYBOARD_GEOMETRIES["ANSI"]
        n_rows = len(active_geom)
        
        frow_ratio = 0.7
        frow_gap = max(3.0, inner_h * 0.015)
        row_h = (inner_h - frow_gap) / (frow_ratio + n_rows - 1)
        frow_h = frow_ratio * row_h

        key_gap = max(2.5, row_h * 0.07)
        radius = max(4.0, row_h * 0.16)
        total_units = max(sum(w for _, w in row) for row in active_geom)

        # Keyboard chassis
        self._rounded_rect(cr, 0, 0, width, height, chassis_r)
        cr.set_source_rgba(*_COL_FRAME_BG)
        cr.fill_preserve()
        cr.set_source_rgba(*_COL_FRAME_BORDER)
        cr.set_line_width(1.0)
        cr.stroke()

        for row_idx, row in enumerate(active_geom):
            if row_idx == 0:
                y = float(pad_y)
                this_row_h = frow_h
            else:
                y = float(pad_y + frow_h + frow_gap + (row_idx - 1) * row_h)
                this_row_h = row_h
            x = float(pad_x)

            for kid, units in row:
                key_w = (units / total_units) * inner_w

                if not kid:
                    x += key_w
                    continue

                label = _STATIC_LABELS.get(kid)
                if label is None:
                    keycode = _KID_TO_KEYCODE.get(kid)
                    if keycode:
                        label = self._xkb.get_label(keycode)
                if label is None:
                    label = kid.upper() if len(kid) <= 1 else kid.capitalize()
                else:
                    label = label.upper() if len(label) == 1 else label

                kx = x + key_gap / 2
                ky = y + key_gap / 2
                kw = key_w - key_gap
                kh = this_row_h - key_gap

                binds   = self._bindings.get(kid, [])
                is_bound  = bool(binds)
                is_sel    = self._selected_id == kid
                is_search = is_bound and self._matches_search(binds)

                if is_sel:
                    fill   = _COL_SEL_BG
                    border = _COL_SEL_BORDER
                    glow   = _COL_SEL_GLOW
                elif is_search:
                    fill   = _COL_SEARCH_BG
                    border = _COL_SEARCH_BORDER
                    glow   = _COL_SEARCH_GLOW
                elif is_bound:
                    fill   = _COL_BOUND_BG
                    border = _COL_BOUND_BORDER
                    glow   = _COL_BOUND_GLOW
                else:
                    fill   = _COL_KEY_BG
                    border = _COL_KEY_BORDER
                    glow   = None

                if glow:
                    for spread, alpha_scale in ((6, 0.15), (3, 0.25), (1, 0.35)):
                        cr.set_source_rgba(glow[0], glow[1], glow[2], glow[3] * alpha_scale)
                        self._rounded_rect(
                            cr,
                            kx - spread, ky - spread,
                            kw + spread * 2, kh + spread * 2,
                            radius + spread,
                        )
                        cr.fill()

                # Key face fill
                self._rounded_rect(cr, kx, ky, kw, kh, radius)
                cr.set_source_rgba(*fill)
                cr.fill_preserve()

                # Key border
                lw = 1.2 if (is_bound or is_sel) else 0.8
                cr.set_source_rgba(*border)
                cr.set_line_width(lw)
                cr.stroke()

                if is_bound:
                    first_mod = self._first_modifier(binds)
                    if first_mod:
                        mod_fs = max(4.5, kh * 0.14)
                        cr.select_font_face("Sans", 0, 1)
                        cr.set_font_size(mod_fs)
                        mx = int(kx + 6)
                        my = int(ky + mod_fs + 5)
                        cr.set_source_rgba(*_COL_BOUND_MOD)
                        cr.move_to(mx, my)
                        cr.show_text(first_mod[:3].upper())

                fs = max(7.0, kh * 0.26)
                cr.select_font_face("Sans", 0, 1)
                cr.set_font_size(fs)
                te = cr.text_extents(label)
                tx = int(kx + (kw - te.width) / 2 - te.x_bearing)
                ty = int(ky + (kh + te.height) / 2 - te.height / 2)

                # Drop shadow
                cr.set_source_rgba(0, 0, 0, 0.5)
                cr.move_to(tx, ty + 1)
                cr.show_text(label)
                cr.set_source_rgba(1.0, 1.0, 1.0, 0.9)
                cr.move_to(tx, ty)
                cr.show_text(label)

                if len(binds) > 1:
                    badge_txt = str(len(binds))
                    bfs = max(5.0, kh * 0.14)
                    cr.select_font_face("Sans", 0, 1)
                    cr.set_font_size(bfs)
                    bte = cr.text_extents(badge_txt)
                    bpad = 2.0
                    bw = bte.width + bpad * 2
                    bh_pill = bte.height + bpad * 2
                    bx = int(kx + kw - bw - 5)
                    by = int(ky + kh - bh_pill - 5)
                    cr.set_source_rgba(*_COL_BADGE_BG)
                    self._rounded_rect(cr, bx, by, bw, bh_pill, bh_pill / 2)
                    cr.fill()
                    cr.set_source_rgba(*_COL_BADGE_FG)
                    cr.move_to(int(bx + bpad - bte.x_bearing), int(by + bpad - bte.y_bearing))
                    cr.show_text(badge_txt)

                self._key_rects.append((kid, kx, ky, kw, kh))
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

    def __init__(self, on_edit=None, on_add=None, on_delete=None):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self._on_edit = on_edit
        self._on_add = on_add
        self._on_delete = on_delete
        self._current_key_id = None
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

        self._header_add_btn = Gtk.Button(icon_name="list-add-symbolic")
        self._header_add_btn.add_css_class("flat")
        self._header_add_btn.add_css_class("circular")
        self._header_add_btn.set_tooltip_text("Add another binding for this key")
        self._header_add_btn.set_valign(Gtk.Align.CENTER)
        self._header_add_btn.set_visible(False)
        self._header_add_btn.connect("clicked", self._on_header_add_clicked)
        header.append(self._header_add_btn)

        self.append(header)

        self.append(Gtk.Separator())


        self._grp_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self._grp_container.set_margin_start(8)
        self._grp_container.set_margin_end(8)
        self._grp_container.set_margin_top(6)
        self._grp_container.set_margin_bottom(8)
        self.append(self._grp_container)

        self.set_visible(False)

    def _on_header_add_clicked(self, *_):
        if self._on_add and self._current_key_id:
            self._on_add(self._current_key_id)

    def update(self, key_id: str, binds: list[dict]):
        self._current_key_id = key_id
        while True:
            c = self._grp_container.get_first_child()
            if c is None:
                break
            self._grp_container.remove(c)

        new_grp = Adw.PreferencesGroup()

        if not binds:
            self._key_label.set_label(key_id.upper())
            self._count_label.set_label("No bindings")
            self._header_add_btn.set_visible(False)
            
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
            self._header_add_btn.set_visible(True)
            for b in binds:
                keysym = b.get("keysym", "?")
                action = b.get("action", "")
                args = b.get("action_args") or []
                arg_str = " ".join(str(a) for a in args)
                full_action = f"{action} {arg_str}".strip() or "(no action)"

                row = Adw.ActionRow(title=GLib.markup_escape_text(full_action))

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

                if b.get("allow_when_locked"):
                    lock = Gtk.Label(label="🔒")
                    lock.set_tooltip_text("Allowed when screen is locked")
                    lock.set_valign(Gtk.Align.CENTER)
                    row.add_suffix(lock)
                    
                edit_btn = Gtk.Button(icon_name="document-edit-symbolic")
                edit_btn.add_css_class("flat")
                edit_btn.add_css_class("circular")
                edit_btn.set_valign(Gtk.Align.CENTER)
                if self._on_edit:
                    edit_btn.connect("clicked", lambda *_, bind_ref=b: self._on_edit(bind_ref))
                row.add_suffix(edit_btn)

                del_btn = Gtk.Button(icon_name="user-trash-symbolic")
                del_btn.add_css_class("flat")
                del_btn.add_css_class("circular")
                del_btn.add_css_class("error")
                del_btn.set_valign(Gtk.Align.CENTER)
                if self._on_delete:
                    del_btn.connect("clicked", lambda *_, bind_ref=b: self._on_delete(bind_ref))
                row.add_suffix(del_btn)

                new_grp.add(row)

        self._grp_container.append(new_grp)
        self.set_visible(True)

