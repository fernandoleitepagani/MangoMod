"""Environment Variables page — MangoWM env= lines."""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk, GLib

from mangomod.pages.base import BasePage

class EnvironmentPage(BasePage):
    def build(self):
        tb, _, _, content = self._make_toolbar_page("Environment")
        self._content = content
        self.refresh()
        return tb

    def refresh(self):
        while True:
            c = self._content.get_first_child()
            if c is None:
                break
            self._content.remove(c)

        entries = self._config.get_all("env")

        if not entries:
            status = Adw.StatusPage(
                title="No Environment Variables",
                description="Variables set here apply to MangoWM and all spawned processes.",
                icon_name="preferences-system-symbolic",
            )
            add = Gtk.Button(label="Add Variable")
            add.add_css_class("pill")
            add.add_css_class("suggested-action")
            add.set_halign(Gtk.Align.CENTER)
            add.connect("clicked", self._on_add)

            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            box.set_valign(Gtk.Align.CENTER)
            box.set_vexpand(True)
            box.append(status)
            box.append(add)
            self._content.append(box)
        else:
            grp = Adw.PreferencesGroup(
                title="Environment Variables",
                description=f"{len(entries)} variable{'s' if len(entries) != 1 else ''} configured",
            )
            with self._suspend():
                for i, entry in enumerate(entries):
                    grp.add(self._make_row(entry, i))
            self._content.append(grp)

            add = Gtk.Button(label="Add Another Variable")
            add.add_css_class("pill")
            add.set_halign(Gtk.Align.CENTER)
            add.set_margin_top(16)
            add.connect("clicked", self._on_add)
            self._content.append(add)

    def _make_row(self, entry: str, idx: int) -> Adw.ActionRow:
        if "," in entry:
            key, _, val = entry.partition(",")
        else:
            key, val = entry, ""

        key_str = GLib.markup_escape_text(key)
        val_str = GLib.markup_escape_text(val)

        row = Adw.ActionRow(
            title=f"<b>{key_str}</b>",
            subtitle=val_str or "(empty)",
        )
        row.set_use_markup(True)

        e = Gtk.Button(icon_name="document-edit-symbolic")
        e.set_valign(Gtk.Align.CENTER)
        e.add_css_class("flat")
        e.connect("clicked", lambda *_, i=idx: self._on_edit(i))
        row.add_suffix(e)

        d = Gtk.Button(icon_name="user-trash-symbolic")
        d.set_valign(Gtk.Align.CENTER)
        d.add_css_class("flat")
        d.add_css_class("error")
        d.connect("clicked", lambda *_, i=idx: self._on_delete(i))
        row.add_suffix(d)
        return row

    def _on_add(self, *_):
        self._show_dialog(None, -1)

    def _on_edit(self, idx):
        entries = self._config.get_all("env")
        if 0 <= idx < len(entries):
            self._show_dialog(entries[idx], idx)

    def _on_delete(self, idx):
        if 0 <= idx < len(self._config.get_all("env")):
            self._config.remove_nth("env", idx)
            self._commit("remove env var")
            GLib.idle_add(self._deferred_refresh)

    def _deferred_refresh(self):
        self.refresh()
        return False

    def _show_dialog(self, entry, idx):
        dialog = Adw.AlertDialog(
            heading="Environment Variable",
            body="Set a KEY,value environment variable.",
        )

        key_row = Adw.EntryRow(title="Variable Name (e.g. QT_QPA_PLATFORM)")
        val_row = Adw.EntryRow(title="Value (e.g. wayland)")

        if entry:
            if "," in entry:
                k, _, v = entry.partition(",")
            else:
                k, v = entry, ""
            key_row.set_text(k)
            key_row.set_editable(False)
            val_row.set_text(v)

        grp = Adw.PreferencesGroup()
        grp.add(key_row)
        grp.add(val_row)
        dialog.set_extra_child(grp)

        dialog.add_response("cancel", "Cancel")
        dialog.add_response("save", "Save")
        dialog.set_response_appearance("save", Adw.ResponseAppearance.SUGGESTED)

        def _on_resp(d, r):
            if r != "save":
                return
            key = key_row.get_text().strip()
            val = val_row.get_text().strip()
            if not key:
                return
            new_entry = f"{key},{val}"

            entries = self._config.get_all("env")
            if 0 <= idx < len(entries):
                self._config.replace_nth("env", idx, new_entry)
            else:
                self._config.add("env", new_entry)

            self._commit("env var")
            GLib.idle_add(self._deferred_refresh)

        dialog.connect("response", _on_resp)
        dialog.present(self._win)
