"""Environment Variables page."""

from __future__ import annotations


import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, GLib, Gtk

from nirimod.kdl_parser import KdlNode, find_or_create
from nirimod.pages.base import BasePage, make_toolbar_page


class EnvironmentPage(BasePage):
    def build(self) -> Gtk.Widget:
        tb, header, _, content = make_toolbar_page("Environment")
        self._content = content

        add_btn = Gtk.Button(icon_name="list-add-symbolic")
        add_btn.add_css_class("flat")
        add_btn.set_tooltip_text("Add variable")
        add_btn.connect("clicked", self._on_add)
        header.pack_end(add_btn)

        self._grp = Adw.PreferencesGroup(
            title="Environment Variables",
            description="Variables set for niri and all spawned processes",
        )
        content.append(self._grp)
        self.refresh()
        return tb

    def refresh(self):
        self._rebuild()

    def _get_env_node(self) -> KdlNode:
        return find_or_create(self._nodes, "environment")

    def _rebuild(self):
        parent = self._grp.get_parent()
        if parent is None:
            return
        env = self._get_env_node()
        entries = list(env.children)
        new_grp = Adw.PreferencesGroup(
            title="Environment Variables", description=f"{len(entries)} variable(s)"
        )
        for i, child in enumerate(entries):
            row = self._make_row(child, i)
            new_grp.add(row)
        parent.remove(self._grp)
        parent.append(new_grp)
        self._grp = new_grp

    def _make_row(self, node: KdlNode, idx: int) -> Adw.ActionRow:
        key = node.name
        val = node.args[0] if node.args else ""
        row = Adw.ActionRow(
            title=GLib.markup_escape_text(key),
            subtitle=GLib.markup_escape_text(str(val)),
        )

        edit_btn = Gtk.Button(icon_name="document-edit-symbolic")
        edit_btn.set_valign(Gtk.Align.CENTER)
        edit_btn.add_css_class("flat")
        edit_btn.connect("clicked", lambda *_, i=idx: self._on_edit(i))
        row.add_suffix(edit_btn)

        del_btn = Gtk.Button(icon_name="user-trash-symbolic")
        del_btn.set_valign(Gtk.Align.CENTER)
        del_btn.add_css_class("flat")
        del_btn.add_css_class("error")
        del_btn.connect("clicked", lambda *_, i=idx: self._on_delete(i))
        row.add_suffix(del_btn)
        return row

    def _on_add(self, *_):
        self._show_dialog(None, -1)

    def _on_edit(self, idx: int):
        env = self._get_env_node()
        if 0 <= idx < len(env.children):
            self._show_dialog(env.children[idx], idx)

    def _on_delete(self, idx: int):
        env = self._get_env_node()
        if 0 <= idx < len(env.children):
            env.children.pop(idx)
            self._commit("remove env var")
            self._rebuild()

    def _show_dialog(self, node: KdlNode | None, idx: int):
        dialog = Adw.AlertDialog(
            heading="Environment Variable", body="Set a key=value environment variable."
        )

        key_entry = Adw.EntryRow(title="Variable Name (e.g. QT_QPA_PLATFORM)")
        val_entry = Adw.EntryRow(title="Value (e.g. wayland)")
        if node:
            key_entry.set_text(node.name)
            key_entry.set_editable(False)  # editing key means replacing the node
            val_entry.set_text(str(node.args[0]) if node.args else "")

        grp = Adw.PreferencesGroup()
        grp.add(key_entry)
        grp.add(val_entry)
        dialog.set_extra_child(grp)

        dialog.add_response("cancel", "Cancel")
        dialog.add_response("save", "Save")
        dialog.set_response_appearance("save", Adw.ResponseAppearance.SUGGESTED)

        def _on_resp(d, r):
            if r != "save":
                return
            key = key_entry.get_text().strip()
            val = val_entry.get_text()
            if not key:
                return
            env = self._get_env_node()
            new_node = KdlNode(key, args=[val])
            if idx >= 0 and 0 <= idx < len(env.children):
                env.children[idx] = new_node
            else:
                env.children.append(new_node)
            self._commit("env var")
            self._rebuild()

        dialog.connect("response", _on_resp)
        dialog.present(self._win)
