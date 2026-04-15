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

# Layout data (ported from src/Main.elm `keyboardLayout`)
# Each entry: (key_id, display_label, width_units)
# One unit ≈ pixel width / 56 * unit_count. Rows total 56 units each.

KEYBOARD_ROWS: list[list[tuple[str, str, int]]] = [
    # Row 1 — number row
    [
        ("escape", "Esc", 4),
        ("1", "1", 4),
        ("2", "2", 4),
        ("3", "3", 4),
        ("4", "4", 4),
        ("5", "5", 4),
        ("6", "6", 4),
        ("7", "7", 4),
        ("8", "8", 4),
        ("9", "9", 4),
        ("0", "0", 4),
        ("minus", "−", 4),
        ("equal", "=", 4),
        ("backspace", "Bksp", 8),
    ],
    # Row 2 — QWERTY
    [
        ("tab", "Tab", 6),
        ("q", "Q", 4),
        ("w", "W", 4),
        ("e", "E", 4),
        ("r", "R", 4),
        ("t", "T", 4),
        ("y", "Y", 4),
        ("u", "U", 4),
        ("i", "I", 4),
        ("o", "O", 4),
        ("p", "P", 4),
        ("bracketleft", "[", 4),
        ("bracketright", "]", 4),
        ("backslash", "\\", 6),
    ],
    # Row 3 — home row
    [
        ("capslock", "Caps", 7),
        ("a", "A", 4),
        ("s", "S", 4),
        ("d", "D", 4),
        ("f", "F", 4),
        ("g", "G", 4),
        ("h", "H", 4),
        ("j", "J", 4),
        ("k", "K", 4),
        ("l", "L", 4),
        ("semicolon", ";", 4),
        ("quote", "'", 4),
        ("return", "Enter", 9),
    ],
    # Row 4 — shift row
    # shiftleft: 7, letters: 40, shiftright: 5, up: 4, spacer: 4 → total 60
    # This puts ↑ at units 52-56, directly above ↓ (also 52-56 in row 5).
    [
        ("shiftleft", "Shift", 7),
        ("z", "Z", 4),
        ("x", "X", 4),
        ("c", "C", 4),
        ("v", "V", 4),
        ("b", "B", 4),
        ("n", "N", 4),
        ("m", "M", 4),
        ("comma", ",", 4),
        ("period", ".", 4),
        ("slash", "/", 4),
        ("shiftright", "Shift", 5),
        ("up", "↑", 4),
        ("", "", 4),  # spacer — keeps row at 60 units
    ],
    # Row 5 — bottom row
    [
        ("ctrlleft", "Ctrl", 6),
        ("superleft", "Super", 6),
        ("altleft", "Alt", 6),
        ("space", "", 24),
        ("altright", "Alt", 6),
        ("left", "←", 4),
        ("down", "↓", 4),
        ("right", "→", 4),
    ],
]

# Keys to skip when building lookup (modifier-only keys don't bind in niri)
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
# (covers special names users put in config.kdl that differ from the id)
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


_COL_KEY_BG = _rgb(30, 30, 30)
_COL_KEY_BORDER = _rgb(255, 255, 255, 0.08)
_COL_KEY_FG = _rgb(200, 200, 200)
_COL_BOUND_BG = _rgb(53, 132, 228, 0.22)
_COL_BOUND_BORDER = _rgb(53, 132, 228, 0.65)
_COL_BOUND_MOD = _rgb(53, 132, 228)
_COL_SEL_BG = _rgb(53, 132, 228, 0.35)
_COL_SEL_BORDER = _rgb(53, 132, 228, 1.0)
_COL_SEARCH_BG = _rgb(192, 97, 203, 0.25)
_COL_SEARCH_BORDER = _rgb(192, 97, 203, 0.8)


class KeyboardVisualizer(Gtk.Box):
    """Cairo-rendered ANSI QWERTY keyboard with niri binding overlays."""

    __gsignals__ = {
        "key-selected": (GObject.SignalFlags.RUN_FIRST, None, (str,)),
    }

    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12)

        # State
        self._bindings: dict[str, list[dict]] = {}  # key_id → [bind_dict, ...]
        self._selected_id: str | None = None
        self._search_q: str = ""

        # Precompute flat list for hit-tests
        self._key_rects: list[tuple[str, float, float, float, float]] = []
        # (key_id, x, y, w, h) — populated on first draw

        # Drawing area
        self._area = Gtk.DrawingArea()
        self._area.set_hexpand(True)
        self._area.set_draw_func(self._draw)

        # Wrap in an AspectFrame so GTK always forces it to an exact 2.8:1 ratio
        # regardless of available height, fixing layout jumps.
        self._aspect_frame = Gtk.AspectFrame(ratio=2.8, obey_child=False)
        self._aspect_frame.set_child(self._area)
        self.append(self._aspect_frame)

        click = Gtk.GestureClick()
        click.connect("released", self._on_click)
        self._area.add_controller(click)

        # We no longer need _on_resize since AspectFrame handles the scaling

        # Action overlay panel
        self._panel = _ActionPanel()
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

        # Margins
        pad_x, pad_y = 10, 8
        inner_w = width - 2 * pad_x
        inner_h = height - 2 * pad_y

        n_rows = len(KEYBOARD_ROWS)
        row_h = inner_h / n_rows
        key_gap = max(2.0, row_h * 0.06)
        radius = max(3.0, row_h * 0.14)

        # Compute max row width from actual layout data (rows are all equal)
        total_units = max(sum(w for _, _, w in row) for row in KEYBOARD_ROWS)

        for row_idx, row in enumerate(KEYBOARD_ROWS):
            y = float(pad_y + row_idx * row_h)
            x = float(pad_x)

            for kid, label, units in row:
                key_w = (units / total_units) * inner_w

                # Spacer key — advance x but draw nothing
                if not kid:
                    x += key_w
                    continue
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
                    lw = 1.5
                elif is_bound:
                    bg, border = _COL_BOUND_BG, _COL_BOUND_BORDER
                    lw = 1.2
                else:
                    bg, border = _COL_KEY_BG, _COL_KEY_BORDER
                    lw = 0.8

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
                    cr.set_source_rgba(53 / 255, 132 / 255, 228 / 255, 0.18)
                    cr.set_line_width(4.0)
                    self._rounded_rect(
                        cr,
                        key_rect_x - 2,
                        key_rect_y - 2,
                        key_rect_w + 4,
                        key_rect_h + 4,
                        radius + 2,
                    )
                    cr.stroke()

                # Modifier badge (top-left tiny text)
                if is_bound and not is_sel:
                    first_mod = self._first_modifier(binds)
                    if first_mod:
                        cr.set_source_rgba(*_COL_BOUND_MOD)
                        cr.select_font_face(
                            "Sans",
                            0,  # SLANT_NORMAL
                            1,
                        )  # WEIGHT_BOLD
                        badge_fs = max(6.0, key_rect_h * 0.16)
                        cr.set_font_size(badge_fs)
                        cr.move_to(key_rect_x + 2.5, key_rect_y + badge_fs + 0.5)
                        cr.show_text(first_mod[:4].upper())

                fs = max(7.0, key_rect_h * 0.30)
                cr.set_font_size(fs)
                cr.select_font_face("Sans", 0, 1)

                if is_bound:
                    cr.set_source_rgba(1, 1, 1, 0.92)
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
                    bfs = max(5.5, key_rect_h * 0.14)
                    cr.set_font_size(bfs)
                    bte = cr.text_extents(badge_txt)
                    bpad = 2.5
                    bw = bte.width + bpad * 2
                    bh = bte.height + bpad * 2
                    bx = key_rect_x + key_rect_w - bw - 2
                    by = key_rect_y + key_rect_h - bh - 2
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
            # Inline CSS per chip color — easiest without a CssProvider per widget
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

        box.append(_chip("rgba(53,132,228,0.6)", "Bound"))
        box.append(_chip("rgba(192,97,203,0.55)", "Search match"))
        box.append(_chip("rgba(53,132,228,1.0)", "Selected"))
        box.append(_chip("rgba(40,40,40,1.0)", "Unbound"))
        return box


# Action overlay panel


class _ActionPanel(Gtk.Box):
    """Shows the binding details for the currently selected key."""

    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
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

        # Stable container — we rebuild the PreferencesGroup inside here each time
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
            row = Adw.ActionRow(title="No niri action bound to this key")
            row.set_sensitive(False)
            new_grp.add(row)
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
