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
        tb, header, _, content = self._make_toolbar_page("Environment")
        self._content = content

        # Add button has been moved to the page body for better visibility
        self.refresh()
        return tb

    def refresh(self):
        self._rebuild()

    def _get_env_node(self) -> KdlNode:
        return find_or_create(self._nodes, "environment")

    def _rebuild(self):
        # Clear existing content
        while True:
            child = self._content.get_first_child()
            if child is None:
                break
            self._content.remove(child)

        env = self._get_env_node()
        entries = list(env.children)

        if not entries:
            status = Adw.StatusPage(
                title="No Environment Variables",
                description="Variables set here will apply to niri and all processes it spawns.",
                icon_name="preferences-system-symbolic",
            )

            add_btn = Gtk.Button(label="Add Variable")
            add_btn.add_css_class("pill")
            add_btn.add_css_class("suggested-action")
            add_btn.set_halign(Gtk.Align.CENTER)
            add_btn.connect("clicked", self._on_add)

            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
            box.set_valign(Gtk.Align.CENTER)
            box.set_vexpand(True)
            box.append(status)
            box.append(add_btn)

            self._content.append(box)
        else:
            grp = Adw.PreferencesGroup(
                title="Environment Variables",
                description=f"{len(entries)} variable{'s' if len(entries) != 1 else ''} configured",
            )
            for i, child in enumerate(entries):
                row = self._make_row(child, i)
                grp.add(row)

            self._content.append(grp)
            
            # Convenient button at the bottom
            add_btn = Gtk.Button(label="Add Another Variable")
            add_btn.add_css_class("pill")
            add_btn.set_halign(Gtk.Align.CENTER)
            add_btn.set_margin_top(16)
            add_btn.connect("clicked", self._on_add)
            self._content.append(add_btn)

    def _make_row(self, node: KdlNode, idx: int) -> Adw.ActionRow:
        key = node.name
        val = node.args[0] if node.args else ""
        
        # Make key bold and distinct
        key_str = GLib.markup_escape_text(key)
        val_str = GLib.markup_escape_text(str(val))
        
        row = Adw.ActionRow(
            title=f"<b>{key_str}</b>",
            subtitle=val_str if val_str else "(empty)",
        )
        row.set_use_markup(True)
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
