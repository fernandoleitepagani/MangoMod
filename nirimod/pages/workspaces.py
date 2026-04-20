"""Workspaces page."""

from __future__ import annotations


import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk

from nirimod.kdl_parser import KdlNode, set_child_arg
from nirimod import niri_ipc
from nirimod.pages.base import BasePage, make_toolbar_page


class WorkspacesPage(BasePage):
    def build(self) -> Gtk.Widget:
        tb, header, _, content = self._make_toolbar_page("Workspaces")
        self._content = content

        add_btn = Gtk.Button(icon_name="list-add-symbolic")
        add_btn.add_css_class("flat")
        add_btn.connect("clicked", self._on_add)
        header.pack_end(add_btn)

        self._grp = Adw.PreferencesGroup(
            title="Named Workspaces",
            description="Named workspaces open immediately at niri startup",
        )
        content.append(self._grp)
        self.refresh()
        return tb

    def refresh(self):
        self._rebuild()

    def _get_ws_nodes(self) -> list[KdlNode]:
        return [n for n in self._nodes if n.name == "workspace"]

    def _rebuild(self):
        parent = self._grp.get_parent()
        if parent is None:
            return

        def _on_outputs(outputs_data):
            ws_nodes = self._get_ws_nodes()
            outputs = [o.get("name", "") for o in outputs_data]
            output_model = Gtk.StringList.new(["(any)"] + outputs)

            new_grp = Adw.PreferencesGroup(
                title="Named Workspaces", description=f"{len(ws_nodes)} workspace(s)"
            )
            for i, ws in enumerate(ws_nodes):
                row = self._make_ws_row(ws, i, outputs, output_model)
                new_grp.add(row)
            parent.remove(self._grp)
            parent.append(new_grp)
            self._grp = new_grp

        niri_ipc.get_outputs(_on_outputs)

    def _make_ws_row(
        self, ws: KdlNode, idx: int, outputs: list[str], output_model: Gtk.StringList
    ) -> Adw.ExpanderRow:
        name = ws.args[0] if ws.args else f"workspace-{idx + 1}"
        assigned_out = ws.child_arg("open-on-output") or ""

        exp = Adw.ExpanderRow(title=name)

        name_row = Adw.EntryRow(title="Name")
        name_row.set_text(str(name))
        name_row.set_show_apply_button(True)
        name_row.connect("apply", lambda r, i=idx: self._rename_ws(i, r.get_text()))
        exp.add_row(name_row)

        out_row = Adw.ComboRow(title="Open on Output")
        out_list = ["(any)"] + outputs
        out_row.set_model(Gtk.StringList.new(out_list))
        if assigned_out in outputs:
            out_row.set_selected(out_list.index(assigned_out))
        out_row.connect(
            "notify::selected",
            lambda r, _, i=idx, ol=out_list: self._set_ws_output(
                i, ol[r.get_selected()]
            ),
        )
        exp.add_row(out_row)

        del_btn = Gtk.Button(icon_name="user-trash-symbolic")
        del_btn.add_css_class("flat")
        del_btn.add_css_class("error")
        del_btn.set_valign(Gtk.Align.CENTER)
        del_btn.connect("clicked", lambda *_, i=idx: self._on_delete(i))
        exp.add_suffix(del_btn)

        return exp

    def _on_add(self, *_):
        dialog = Adw.AlertDialog(
            heading="Add Workspace", body="Enter a name for the new workspace."
        )
        entry = Adw.EntryRow(title="Workspace Name")
        grp = Adw.PreferencesGroup()
        grp.add(entry)
        dialog.set_extra_child(grp)
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("add", "Add")
        dialog.set_response_appearance("add", Adw.ResponseAppearance.SUGGESTED)

        def _on_resp(d, r):
            if r != "add":
                return
            name = entry.get_text().strip()
            if not name:
                return
            node = KdlNode("workspace", args=[name])
            ws_nodes = self._get_ws_nodes()
            if ws_nodes:
                last_idx = self._nodes.index(ws_nodes[-1])
                self._nodes.insert(last_idx + 1, node)
            else:
                # If no workspaces, insert at the top
                self._nodes.insert(0, node)
            self._commit("add workspace")
            self._rebuild()

        dialog.connect("response", _on_resp)
        dialog.present(self._win)

    def _on_delete(self, idx: int):
        ws_nodes = self._get_ws_nodes()
        if 0 <= idx < len(ws_nodes):
            self._nodes.remove(ws_nodes[idx])
            self._commit("remove workspace")
            self._rebuild()

    def _rename_ws(self, idx: int, name: str):
        ws_nodes = self._get_ws_nodes()
        if 0 <= idx < len(ws_nodes) and name.strip():
            ws_nodes[idx].args = [name.strip()]
            self._commit("rename workspace")
            self._rebuild()

    def _set_ws_output(self, idx: int, output: str):
        ws_nodes = self._get_ws_nodes()
        if 0 <= idx < len(ws_nodes):
            ws = ws_nodes[idx]
            if output and output != "(any)":
                set_child_arg(ws, "open-on-output", output)
            else:
                from nirimod.kdl_parser import remove_child

                remove_child(ws, "open-on-output")
            self._commit("workspace output")
