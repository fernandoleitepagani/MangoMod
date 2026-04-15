"""Startup Programs page."""

from __future__ import annotations


import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk, GLib

from nirimod.kdl_parser import KdlNode
from nirimod.pages.base import BasePage, make_toolbar_page


class StartupPage(BasePage):
    def build(self) -> Gtk.Widget:
        tb, header, _, content = make_toolbar_page("Startup Programs")
        self._content = content

        add_btn = Gtk.Button(icon_name="list-add-symbolic")
        add_btn.add_css_class("flat")
        add_btn.set_tooltip_text("Add startup entry")
        add_btn.connect("clicked", self._on_add)
        header.pack_end(add_btn)

        self._grp = Adw.PreferencesGroup(
            title="Startup Programs",
            description="Programs launched automatically when niri starts",
        )
        content.append(self._grp)
        self.refresh()
        return tb

    def refresh(self):
        self._rebuild()

    def _get_entries(self) -> list[KdlNode]:
        return [
            n
            for n in self._nodes
            if n.name in ("spawn-at-startup", "spawn-sh-at-startup")
        ]

    def _rebuild(self):
        parent = self._grp.get_parent()
        if parent is None:
            return
        entries = self._get_entries()
        new_grp = Adw.PreferencesGroup(
            title="Startup Programs",
            description=f"{len(entries)} entr{'ies' if len(entries) != 1 else 'y'}",
        )
        for i, entry in enumerate(entries):
            row = self._make_row(entry, i)
            new_grp.add(row)
        parent.remove(self._grp)
        parent.append(new_grp)
        self._grp = new_grp

    def _make_row(self, node: KdlNode, idx: int) -> Adw.ActionRow:
        cmd = " ".join(str(a) for a in node.args)
        is_sh = "sh" in node.name
        row = Adw.ActionRow(
            title=GLib.markup_escape_text(cmd) if cmd else "(empty)",
            subtitle="shell" if is_sh else "direct",
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
        entries = self._get_entries()
        if 0 <= idx < len(entries):
            self._show_dialog(entries[idx], idx)

    def _on_delete(self, idx: int):
        entries = self._get_entries()
        if 0 <= idx < len(entries):
            self._nodes.remove(entries[idx])
            self._commit("remove startup entry")
            self._rebuild()

    def _show_dialog(self, node: KdlNode | None, idx: int):
        dialog = Adw.AlertDialog(
            heading="Startup Program", body="Enter the command to launch at startup."
        )
        cmd_entry = Adw.EntryRow(title="Command")
        sh_switch = Adw.SwitchRow(title="Use shell (spawn-sh-at-startup)")
        if node:
            cmd_entry.set_text(" ".join(str(a) for a in node.args))
            sh_switch.set_active("sh" in node.name)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        grp = Adw.PreferencesGroup()
        grp.add(cmd_entry)
        grp.add(sh_switch)
        box.append(grp)
        dialog.set_extra_child(box)

        dialog.add_response("cancel", "Cancel")
        dialog.add_response("save", "Save")
        dialog.set_response_appearance("save", Adw.ResponseAppearance.SUGGESTED)

        def _on_resp(d, r):
            if r != "save":
                return
            cmd = cmd_entry.get_text().strip()
            if not cmd:
                return
            is_sh = sh_switch.get_active()
            node_name = "spawn-sh-at-startup" if is_sh else "spawn-at-startup"
            new_node = KdlNode(node_name, args=cmd.split())
            entries = self._get_entries()
            if idx >= 0 and 0 <= idx < len(entries):
                i = self._nodes.index(entries[idx])
                self._nodes[i] = new_node
            else:
                self._nodes.append(new_node)
            self._commit("startup entry")
            self._rebuild()

        dialog.connect("response", _on_resp)
        dialog.present(self._win)
