"""Key Bindings page — MangoWM bind= lines."""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk, GLib

from mangomod.pages.base import BasePage

MODIFIERS = ["MOD", "SUPER", "SHIFT", "CTRL", "ALT"]

MANGO_ACTIONS = [
    "spawn", "spawn_shell", "killclient", "quit", "restart",
    "togglefloating", "togglefullscreen", "toggleglobal",
    "view", "tag", "toggleview", "toggletag",
    "focusstack", "focusmon", "tagmon", "zoom",
    "incnmaster", "setmfact", "setcfact", "setgaps",
    "toggleoverview", "toggle_hotarea", "reload_config",
    "movewindow", "resizewindow", "focusdir",
    "exchange_client", "exchange_stack_client",
    "setlayout", "switch_layout", "focuslast",
    "movecenter", "moveabsolute", "movetotag",
    "movetomon", "move", "resize", "killunsel",
]


class BindingsPage(BasePage):
    def __init__(self, window):
        super().__init__(window)
        self._search = ""
        self._rebuild_source: int | None = None

    def build(self):
        tb = Adw.ToolbarView()

        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        header.set_margin_start(24)
        header.set_margin_end(24)
        header.set_margin_top(20)
        header.set_margin_bottom(12)

        title_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        title_box.set_hexpand(True)
        t = Gtk.Label(label="Keybindings")
        t.set_xalign(0.0)
        t.add_css_class("title-1")
        title_box.append(t)
        self._stats = Gtk.Label(label="")
        self._stats.set_xalign(0.0)
        self._stats.add_css_class("dim-label")
        self._stats.add_css_class("caption")
        title_box.append(self._stats)
        header.append(title_box)

        add = Gtk.Button(icon_name="list-add-symbolic")
        add.set_tooltip_text("Add binding")
        add.add_css_class("flat")
        add.add_css_class("circular")
        add.set_valign(Gtk.Align.CENTER)
        add.connect("clicked", lambda *_: self._show_dialog(None, -1))
        header.append(add)

        main = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        main.append(header)

        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        content.set_margin_start(32)
        content.set_margin_end(32)
        content.set_margin_top(24)
        content.set_margin_bottom(32)
        scroll.set_child(content)

        search = Gtk.SearchEntry(placeholder_text="Filter bindings…")
        search.connect("search-changed", self._on_search)
        content.append(search)

        self._listbox = Gtk.ListBox()
        self._listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        self._listbox.add_css_class("boxed-list")
        content.append(self._listbox)

        main.append(scroll)
        tb.set_content(main)

        self.refresh()
        return tb

    def refresh(self):
        """Rebuild the listbox. Safe to call multiple times."""
        if self._rebuild_source is not None:
            GLib.source_remove(self._rebuild_source)
            self._rebuild_source = None

        while True:
            c = self._listbox.get_first_child()
            if c is None:
                break
            self._listbox.remove(c)

        binds = self._config.get_all("bind")
        q = self._search.lower()
        shown = 0
        with self._suspend():
            for i, bind in enumerate(binds):
                if q and q not in bind.lower():
                    continue
                row = self._make_row(bind, i)
                self._listbox.append(row)
                shown += 1

        self._stats.set_label(f"{len(binds)} bindings ({shown} shown)")

    def _on_search(self, entry):
        self._search = entry.get_text().strip()
        if self._rebuild_source is not None:
            GLib.source_remove(self._rebuild_source)
        self._rebuild_source = GLib.timeout_add(120, self._debounced_rebuild)

    def _debounced_rebuild(self):
        self._rebuild_source = None
        self.refresh()
        return False

    def _make_row(self, bind: str, idx: int) -> Adw.ActionRow:
        parts = bind.split(",")
        keys = "+".join(parts[0:2]) if len(parts) >= 2 else bind
        action = parts[2] if len(parts) > 2 else ""
        args = ", ".join(parts[3:]) if len(parts) > 3 else ""

        action_str = f"{action} {args}".strip() or "(unassigned)"
        row = Adw.ActionRow(title=action_str, subtitle=keys)
        row.set_activatable(True)
        row.add_css_class("monospace")

        e = Gtk.Button(icon_name="document-edit-symbolic")
        e.set_valign(Gtk.Align.CENTER)
        e.add_css_class("flat")
        e.connect("clicked", lambda *_, b=bind, i=idx: self._show_dialog(b, i))
        row.add_suffix(e)

        d = Gtk.Button(icon_name="user-trash-symbolic")
        d.set_valign(Gtk.Align.CENTER)
        d.add_css_class("flat")
        d.add_css_class("error")
        d.connect("clicked", lambda *_, i=idx: self._on_delete(i))
        row.add_suffix(d)

        row.connect("activated", lambda *_, b=bind, i=idx: self._show_dialog(b, i))
        return row

    def _on_delete(self, idx):
        if 0 <= idx < len(self._config.get_all("bind")):
            self._config.remove_nth("bind", idx)
            self._commit("remove binding")
            GLib.idle_add(self._deferred_refresh)

    def _deferred_refresh(self):
        self.refresh()
        return False

    def _show_dialog(self, bind: str | None, idx: int):
        dialog = Adw.Dialog(title="Edit Binding" if bind else "Add Binding")
        dialog.set_content_width(480)

        tv = Adw.ToolbarView()
        hdr = Adw.HeaderBar()
        hdr.set_title_widget(Adw.WindowTitle(title=dialog.get_title()))
        tv.add_top_bar(hdr)

        prefs = Adw.PreferencesPage()
        keys_grp = Adw.PreferencesGroup(title="Key Combination")

        parts = bind.split(",") if bind else []
        cur_mods = parts[0].split("+") if parts else []
        cur_key = parts[1] if len(parts) > 1 else ""

        mod_row = Adw.ActionRow(title="Modifiers")
        mod_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        mod_box.set_valign(Gtk.Align.CENTER)
        mod_checks: dict[str, Gtk.CheckButton] = {}
        for m in MODIFIERS:
            cb = Gtk.CheckButton(label=m.title())
            cb.set_active(m in cur_mods)
            mod_box.append(cb)
            mod_checks[m] = cb
        mod_row.add_suffix(mod_box)
        keys_grp.add(mod_row)

        key_row = Adw.EntryRow(title="Key (e.g. T, F1, Return)")
        key_row.set_text(cur_key)
        keys_grp.add(key_row)
        prefs.add(keys_grp)

        act_grp = Adw.PreferencesGroup(title="Action")
        act_model = Gtk.StringList.new(MANGO_ACTIONS)
        act_combo = Adw.ComboRow(title="Action", model=act_model)
        cur_action = parts[2] if len(parts) > 2 else ""
        if cur_action in MANGO_ACTIONS:
            act_combo.set_selected(MANGO_ACTIONS.index(cur_action))
        act_grp.add(act_combo)

        arg_row = Adw.EntryRow(title="Argument (e.g. kitty, 1, 0.5)")
        arg_row.set_text(", ".join(parts[3:]) if len(parts) > 3 else "")
        act_grp.add(arg_row)
        prefs.add(act_grp)

        tv.set_content(prefs)

        bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        bar.set_halign(Gtk.Align.END)
        bar.set_margin_start(16)
        bar.set_margin_end(16)
        bar.set_margin_top(8)
        bar.set_margin_bottom(16)

        cancel = Gtk.Button(label="Cancel")
        cancel.add_css_class("pill")
        cancel.connect("clicked", lambda *_: dialog.close())
        bar.append(cancel)

        save = Gtk.Button(label="Save")
        save.add_css_class("suggested-action")
        save.add_css_class("pill")
        bar.append(save)
        tv.add_bottom_bar(bar)

        def _do_save(*_):
            mods = [m for m, cb in mod_checks.items() if cb.get_active()]
            key = key_row.get_text().strip()
            if not key or not mods:
                return
            mods_str = "+".join(mods)
            a_idx = act_combo.get_selected()
            action = MANGO_ACTIONS[a_idx] if a_idx < len(MANGO_ACTIONS) else ""
            arg = arg_row.get_text().strip()

            new_bind = f"{mods_str},{key},{action}"
            if arg:
                new_bind += f",{arg}"

            binds = self._config.get_all("bind")
            if 0 <= idx < len(binds):
                self._config.replace_nth("bind", idx, new_bind)
            else:
                self._config.add("bind", new_bind)

            self._commit("binding")
            dialog.close()
            GLib.idle_add(self._deferred_refresh)

        save.connect("clicked", _do_save)
        dialog.set_child(tv)
        dialog.present(self._win)
