"""Key Bindings page — list editor + keyboard map visualizer.

Tab 1: "Bindings List"    — the original Adw row-based editor (unchanged logic).
Tab 2: "Keyboard Map"     — Cairo keyboard visualizer ported from omer-biz/visu.
"""

from __future__ import annotations


import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gio, GLib, Gtk

from nirimod.kdl_parser import KdlNode
from nirimod.pages.base import BasePage, make_toolbar_page
from nirimod.widgets import KeyboardVisualizer, normalize_key_id


MODIFIERS = ["Super", "Ctrl", "Alt", "Shift"]

NIRI_ACTIONS = [
    "close-window",
    "focus-column-left",
    "focus-column-right",
    "focus-column-first",
    "focus-column-last",
    "focus-window-down",
    "focus-window-up",
    "move-column-left",
    "move-column-right",
    "move-column-to-first",
    "move-column-to-last",
    "move-window-down",
    "move-window-up",
    "focus-workspace-down",
    "focus-workspace-up",
    "focus-workspace",
    "move-column-to-workspace",
    "move-column-to-workspace-down",
    "move-column-to-workspace-up",
    "move-workspace-down",
    "move-workspace-up",
    "focus-monitor-left",
    "focus-monitor-right",
    "focus-monitor-up",
    "focus-monitor-down",
    "move-column-to-monitor-left",
    "move-column-to-monitor-right",
    "move-column-to-monitor-down",
    "move-column-to-monitor-up",
    "maximize-column",
    "fullscreen-window",
    "maximize-window-to-edges",
    "switch-preset-column-width",
    "switch-preset-window-height",
    "set-column-width",
    "set-window-height",
    "reset-window-height",
    "center-column",
    "center-visible-columns",
    "screenshot",
    "screenshot-screen",
    "screenshot-window",
    "spawn",
    "spawn-sh",
    "quit",
    "power-off-monitors",
    "toggle-window-floating",
    "switch-focus-between-floating-and-tiling",
    "toggle-column-tabbed-display",
    "toggle-overview",
    "consume-or-expel-window-left",
    "consume-or-expel-window-right",
    "consume-window-into-column",
    "expel-window-from-column",
    "expand-column-to-available-width",
    "show-hotkey-overlay",
    "toggle-keyboard-shortcuts-inhibit",
    "toggle-windowed-fullscreen",
]


_KNOWN_BIND_PROPS = {"allow-when-locked", "repeat"}


def _make_bind(
    keysym: str,
    action: str,
    action_args: list | None = None,
    allow_when_locked: bool = False,
    repeat: bool = True,
    extra_props: dict | None = None,
) -> dict:
    return {
        "keysym": keysym,
        "action": action,
        "action_args": action_args or [],
        "allow_when_locked": allow_when_locked,
        "repeat": repeat,
        "extra_props": extra_props or {},
    }


def _parse_binds_from_nodes(nodes: list[KdlNode]) -> list[dict]:
    """Parse all bind nodes from the binds block."""
    binds_node = next((n for n in nodes if n.name == "binds"), None)
    if not binds_node:
        return []
    result = []
    for child in binds_node.children:
        keysym = child.name
        action = ""
        action_args: list = []
        allow_locked = child.props.get("allow-when-locked", False)
        repeat = child.props.get("repeat", True)
        extra_props = {
            k: v for k, v in child.props.items() if k not in _KNOWN_BIND_PROPS
        }
        for sub in child.children:
            action = sub.name
            action_args = list(sub.args)
        result.append(
            _make_bind(
                keysym,
                action,
                action_args,
                bool(allow_locked),
                bool(repeat),
                extra_props,
            )
        )
    return result


def _write_binds_to_node(binds_list: list[dict], binds_node: KdlNode):
    """Rewrite the binds block's children from a list of bind dicts."""
    binds_node.children.clear()
    for b in binds_list:
        child = KdlNode(name=b["keysym"])
        if b["allow_when_locked"]:
            child.props["allow-when-locked"] = True
        if not b["repeat"]:
            child.props["repeat"] = False
        for k, v in b.get("extra_props", {}).items():
            child.props[k] = v
        if b["action"]:
            action_node = KdlNode(name=b["action"])
            args = b.get("action_args") or []
            if not args:
                legacy = b.get("action_arg", "")
                if legacy:
                    args = [legacy]
            action_node.args = list(args)
            child.children.append(action_node)
        binds_node.children.append(child)


def _build_key_bindings_map(binds: list[dict]) -> dict[str, list[dict]]:
    """Group binds by their normalised keyboard key-id."""
    result: dict[str, list[dict]] = {}
    for b in binds:
        keysym = b.get("keysym", "")
        raw_key = keysym.split("+")[-1]
        kid = normalize_key_id(raw_key)
        result.setdefault(kid, []).append(b)
    return result


# BindingsPage


class BindingsPage(BasePage):
    def __init__(self, window):
        super().__init__(window)
        self._binds: list[dict] = []
        self._search_query = ""
        self._kb_search_query = ""
        self._file_monitor: Gio.FileMonitor | None = None
        self._viz: KeyboardVisualizer | None = None

    def build(self) -> Gtk.Widget:
        tb, header, _, content = make_toolbar_page("Key Bindings")

        # View switcher in header
        self._view_stack = Adw.ViewStack()

        switcher = Adw.ViewSwitcher()
        switcher.set_stack(self._view_stack)
        switcher.set_policy(Adw.ViewSwitcherPolicy.WIDE)
        header.set_title_widget(switcher)

        list_page_widget = self._build_list_tab()
        self._view_stack.add_titled_with_icon(
            list_page_widget, "list", "Bindings List", "view-list-symbolic"
        )

        self._add_btn_in_header = self._add_btn
        header.pack_end(self._add_btn_in_header)

        kb_page_widget = self._build_keyboard_tab()
        self._view_stack.add_titled_with_icon(
            kb_page_widget, "keyboard", "Keyboard Map", "input-keyboard-symbolic"
        )

        # Stack goes into the scrollable content area
        # But we don't want it scrolled — replace content's child approach:
        # Instead, put the ViewStack directly in the ToolbarView content
        # (bypassing the inner scroll, since the keyboard tab manages its own scroll)
        tb.set_content(self._view_stack)

        self.refresh()
        self._start_file_monitor()
        return tb

    def _build_list_tab(self) -> Gtk.Widget:
        """Return the scrollable list editor widget (original UI)."""
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_vexpand(True)

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        content.set_margin_start(32)
        content.set_margin_end(32)
        content.set_margin_top(24)
        content.set_margin_bottom(32)
        scroll.set_child(content)

        # Add button — we'll wire it via a header-bar button stashed on the page
        self._add_btn = Gtk.Button(icon_name="list-add-symbolic")
        self._add_btn.set_tooltip_text("Add binding")
        self._add_btn.add_css_class("flat")
        self._add_btn.connect("clicked", self._on_add_clicked)

        # Hook into view stack page-change to show/hide the add button
        self._view_stack.connect("notify::visible-child", self._on_tab_changed)
        # We'll inject it into the headerbar from on_shown after build
        self._header_ref = None  # set below
        # Store reference to header so we can add the add-btn later
        # (make_toolbar_page returns it; we get it via the ToolbarView's top bar)

        # Attach add-btn to first page's visible state
        # The simplest approach: always show in header, only enable on list tab
        # We'll handle visibility in _on_tab_changed.

        # Search
        search = Gtk.SearchEntry(placeholder_text="Filter bindings…")
        search.set_margin_start(0)
        search.set_margin_end(0)
        search.connect("search-changed", self._on_filter_changed)
        content.append(search)

        # Binds group
        self._binds_grp = Adw.PreferencesGroup(title="Managed Bindings")
        content.append(self._binds_grp)

        self._list_content = content
        return scroll

    def _build_keyboard_tab(self) -> Gtk.Widget:
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_vexpand(True)

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        outer.set_margin_start(24)
        outer.set_margin_end(24)
        outer.set_margin_top(20)
        outer.set_margin_bottom(24)
        scroll.set_child(outer)

        # Search bar
        kb_search = Gtk.SearchEntry(
            placeholder_text="Filter by action… (e.g. spawn, focus)"
        )
        kb_search.connect("search-changed", self._on_kb_search_changed)
        outer.append(kb_search)

        # Stats label
        self._kb_stats = Gtk.Label(label="")
        self._kb_stats.add_css_class("dim-label")
        self._kb_stats.add_css_class("caption")
        self._kb_stats.set_xalign(0.0)
        outer.append(self._kb_stats)

        # Keyboard visualizer
        self._viz = KeyboardVisualizer()
        self._viz.connect("key-selected", self._on_kb_key_selected)
        outer.append(self._viz)

        return scroll

    # Tab switching

    def _on_tab_changed(self, stack, _param):
        child = stack.get_visible_child_name()
        # Show add-button only on list tab
        if hasattr(self, "_add_btn_in_header"):
            self._add_btn_in_header.set_visible(child == "list")

    # Refresh / sync

    def refresh(self):
        self._binds = _parse_binds_from_nodes(self._nodes)
        self._rebuild_list()
        self._refresh_visualizer()

    def on_shown(self):
        self._refresh_visualizer()

    def _refresh_visualizer(self):
        if self._viz is None:
            return
        binds_map = _build_key_bindings_map(self._binds)
        self._viz.set_bindings(binds_map)
        self._viz.set_search(self._kb_search_query)
        n_bound = len(binds_map)
        n_total = len(self._binds)
        self._kb_stats.set_label(
            f"{n_total} total bindings · {n_bound} unique keys bound"
        )

    # List editor helpers (unchanged from original)

    def _rebuild_list(self):
        box_parent = self._binds_grp.get_parent()
        if box_parent is None:
            return

        new_grp = Adw.PreferencesGroup(
            title="Managed Bindings", description=f"{len(self._binds)} bindings"
        )
        q = self._search_query.lower()
        for i, b in enumerate(self._binds):
            if q and q not in b["keysym"].lower() and q not in b["action"].lower():
                continue
            row = self._make_bind_row(b, i)
            new_grp.add(row)

        idx = 0
        child = box_parent.get_first_child()
        while child:
            if child is self._binds_grp:
                break
            idx += 1
            child = child.get_next_sibling()
        box_parent.remove(self._binds_grp)
        box_parent.append(new_grp)
        self._binds_grp = new_grp

    def _make_bind_row(self, b: dict, idx: int) -> Adw.ActionRow:
        keysym = b["keysym"]
        action = b["action"]
        action_args = b.get("action_args") or []
        action_arg_display = " ".join(str(a) for a in action_args)

        full_action = f"{action}  {action_arg_display}".strip()
        if not full_action:
            full_action = "(unassigned action)"

        # The row title is the action. The shortcut is the prefix.
        row = Adw.ActionRow(title=GLib.markup_escape_text(full_action))

        # Elegant Keycap Prefix
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
                label_text = label_text.upper() if len(label_text) == 1 else label_text

            cap = Gtk.Label(label=label_text)
            if is_mod:
                cap.add_css_class("nm-keycap-mod")
            else:
                cap.add_css_class("nm-keycap-main")
            keys_box.append(cap)

        row.add_prefix(keys_box)

        # Clean Suffix Buttons
        actions_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        actions_box.set_valign(Gtk.Align.CENTER)
        actions_box.set_margin_start(16)

        if b["allow_when_locked"]:
            lock_badge = Gtk.Label(label="🔒")
            lock_badge.set_tooltip_text("Allowed when locked")
            lock_badge.set_valign(Gtk.Align.CENTER)
            actions_box.append(lock_badge)

        edit_btn = Gtk.Button(icon_name="document-edit-symbolic")
        edit_btn.set_valign(Gtk.Align.CENTER)
        edit_btn.add_css_class("circular")
        edit_btn.add_css_class("flat")
        edit_btn.set_tooltip_text("Edit Binding")
        edit_btn.connect("clicked", lambda *_, i=idx: self._on_edit_clicked(i))
        actions_box.append(edit_btn)

        del_btn = Gtk.Button(icon_name="user-trash-symbolic")
        del_btn.set_valign(Gtk.Align.CENTER)
        del_btn.add_css_class("circular")
        del_btn.add_css_class("flat")
        del_btn.add_css_class("error")
        del_btn.set_tooltip_text("Delete Binding")
        del_btn.connect("clicked", lambda *_, i=idx: self._on_delete_clicked(i))
        actions_box.append(del_btn)

        row.add_suffix(actions_box)

        return row

    def _on_filter_changed(self, entry):
        self._search_query = entry.get_text().strip()
        self._rebuild_list()

    def _on_kb_search_changed(self, entry):
        self._kb_search_query = entry.get_text().strip()
        if self._viz:
            self._viz.set_search(self._kb_search_query)

    def _on_kb_key_selected(self, viz, key_id: str):
        # The visualizer's action panel already updates itself;
        # we can optionally jump to the list tab and highlight the binding.
        pass

    def _on_delete_clicked(self, idx: int):
        if 0 <= idx < len(self._binds):
            del self._binds[idx]
            self._save_binds()
            self._rebuild_list()
            self._refresh_visualizer()

    def _on_add_clicked(self, *_):
        self._show_bind_dialog(None, -1)

    def _on_edit_clicked(self, idx: int):
        if 0 <= idx < len(self._binds):
            self._show_bind_dialog(self._binds[idx], idx)

    def _show_bind_dialog(self, bind: dict | None, idx: int):
        dialog = Adw.Dialog(title="Edit Binding" if bind else "Add Binding")
        dialog.set_content_width(440)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        header = Adw.HeaderBar()
        header.set_title_widget(Adw.WindowTitle(title=dialog.get_title()))
        box.append(header)

        prefs = Adw.PreferencesPage()
        prefs.set_vexpand(True)

        # Keysym group
        keys_grp = Adw.PreferencesGroup(title="Key Combination")

        mod_row = Adw.ActionRow(title="Modifiers")
        mod_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        mod_box.set_valign(Gtk.Align.CENTER)
        mod_checks: dict[str, Gtk.CheckButton] = {}
        cur_keysym = bind["keysym"] if bind else ""
        for mod in MODIFIERS:
            cb = Gtk.CheckButton(label=mod)
            cb.set_active(
                mod.lower() in cur_keysym.lower()
                or ("mod" in cur_keysym.lower() and mod == "Super")
            )
            mod_box.append(cb)
            mod_checks[mod] = cb
        mod_row.add_suffix(mod_box)
        keys_grp.add(mod_row)

        key_entry = Adw.EntryRow(title="Key (e.g. T, F1, Return)")
        bare = cur_keysym.split("+")[-1] if bind else ""
        key_entry.set_text(bare)
        keys_grp.add(key_entry)
        prefs.add(keys_grp)

        # Action group
        act_grp = Adw.PreferencesGroup(title="Action")
        act_model = Gtk.StringList.new(NIRI_ACTIONS)
        act_combo = Adw.ComboRow(title="Action", model=act_model)
        cur_action = bind["action"] if bind else ""
        if cur_action in NIRI_ACTIONS:
            act_combo.set_selected(NIRI_ACTIONS.index(cur_action))
        act_grp.add(act_combo)

        arg_row = Adw.EntryRow(title="Argument (for spawn, focus-workspace, etc.)")
        cur_args = (bind.get("action_args") or []) if bind else []
        arg_row.set_text(" ".join(str(a) for a in cur_args) if cur_args else "")
        act_grp.add(arg_row)
        prefs.add(act_grp)

        # Options
        opt_grp = Adw.PreferencesGroup(title="Options")
        locked_row = Adw.SwitchRow(title="Allow When Locked")
        locked_row.set_active(bind["allow_when_locked"] if bind else False)
        opt_grp.add(locked_row)

        repeat_row = Adw.SwitchRow(title="Repeat")
        repeat_row.set_active(bind["repeat"] if bind else True)
        opt_grp.add(repeat_row)
        prefs.add(opt_grp)

        box.append(prefs)

        save_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        save_row.set_halign(Gtk.Align.END)
        save_row.set_margin_start(16)
        save_row.set_margin_end(16)
        save_row.set_margin_top(8)
        save_row.set_margin_bottom(16)
        save_btn = Gtk.Button(label="Save")
        save_btn.add_css_class("suggested-action")
        save_btn.add_css_class("pill")

        def _do_save(*_):
            mods = [m for m, cb in mod_checks.items() if cb.get_active()]
            key = key_entry.get_text().strip()
            if not key:
                return
            mod_parts = []
            for m in mods:
                mod_parts.append("Mod" if m == "Super" else m)
            keysym = "+".join(mod_parts + [key])
            action_idx = act_combo.get_selected()
            action = NIRI_ACTIONS[action_idx] if action_idx < len(NIRI_ACTIONS) else ""
            arg_text = arg_row.get_text().strip()
            new_args = arg_text.split() if arg_text else []
            new_bind = _make_bind(
                keysym,
                action,
                new_args,
                locked_row.get_active(),
                repeat_row.get_active(),
                bind.get("extra_props", {}) if bind else {},
            )
            if idx >= 0:
                self._binds[idx] = new_bind
            else:
                self._binds.append(new_bind)
            self._save_binds()
            self._rebuild_list()
            self._refresh_visualizer()
            dialog.close()

        save_btn.connect("clicked", _do_save)
        save_row.append(save_btn)
        box.append(save_row)

        dialog.set_child(box)
        dialog.present(self._win)

    def _save_binds(self):
        nodes = self._nodes
        binds_node = next((n for n in nodes if n.name == "binds"), None)
        if binds_node is None:
            binds_node = KdlNode("binds")
            nodes.append(binds_node)
        _write_binds_to_node(self._binds, binds_node)
        self._commit("keybindings")

    # File monitor (live-sync)

    def _start_file_monitor(self):
        try:
            from nirimod.kdl_parser import NIRI_CONFIG

            gfile = Gio.File.new_for_path(str(NIRI_CONFIG))
            monitor = gfile.monitor_file(Gio.FileMonitorFlags.NONE, None)
            monitor.connect("changed", self._on_config_file_changed)
            self._file_monitor = monitor
        except Exception:
            pass

    def _on_config_file_changed(self, monitor, file, other_file, event_type):
        if event_type in (Gio.FileMonitorEvent.CHANGED, Gio.FileMonitorEvent.CREATED):
            GLib.timeout_add(400, self._reload_from_disk)

    def _reload_from_disk(self):
        self._win.notify_nodes_changed()
        return False  # don't repeat
