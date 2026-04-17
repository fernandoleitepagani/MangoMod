"""Window Rules page."""

from __future__ import annotations


import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk, GLib

from nirimod.kdl_parser import KdlNode
from nirimod.pages.base import BasePage, make_toolbar_page


BOOL_MATCH_FIELDS = ["is-active", "is-floating", "is-focused", "at-startup"]
STR_MATCH_FIELDS = ["app-id", "title"]
BOOL_ACTIONS = [
    "open-maximized",
    "open-fullscreen",
    "open-floating",
    "block-out-from-screencast",
    "draw-border-with-background",
    "clip-to-geometry",
]
NUM_ACTIONS = [
    "opacity",
    "geometry-corner-radius",
    "min-width",
    "min-height",
    "max-width",
    "max-height",
    "default-window-height",
]
STR_ACTIONS = ["open-on-workspace", "open-on-output", "default-column-width"]


class WindowRulesPage(BasePage):
    def build(self) -> Gtk.Widget:
        tb, header, _, content = make_toolbar_page("Window Rules")
        self._content = content

        add_btn = Gtk.Button(icon_name="list-add-symbolic")
        add_btn.add_css_class("flat")
        add_btn.set_tooltip_text("Add rule")
        add_btn.connect("clicked", self._on_add)
        header.pack_end(add_btn)

        add_layer_btn = Gtk.Button(icon_name="list-add-symbolic")
        add_layer_btn.add_css_class("flat")
        add_layer_btn.set_tooltip_text("Add layer rule")
        add_layer_btn.connect("clicked", self._on_add_layer)
        header.pack_end(add_layer_btn)

        self._rules_grp = Adw.PreferencesGroup(title="Window Rules")
        content.append(self._rules_grp)

        self._layer_rules_grp = Adw.PreferencesGroup(
            title="Layer Rules",
            description="Rules for layer-shell surfaces (bars, overlays, etc.)",
        )
        content.append(self._layer_rules_grp)

        self.refresh()
        return tb

    def refresh(self):
        self._rebuild()
        self._rebuild_layer()

    def _get_layer_rules(self) -> list[KdlNode]:
        return [n for n in self._nodes if n.name == "layer-rule"]

    def _rebuild_layer(self):
        parent = self._layer_rules_grp.get_parent()
        if parent is None:
            return
        rules = self._get_layer_rules()
        new_grp = Adw.PreferencesGroup(
            title="Layer Rules",
            description=f"{len(rules)} layer rule(s) — for bars, overlays, etc.",
        )
        for i, rule in enumerate(rules):
            row = self._make_layer_rule_row(rule, i)
            new_grp.add(row)
        parent.remove(self._layer_rules_grp)
        parent.append(new_grp)
        self._layer_rules_grp = new_grp

    def _make_layer_rule_row(self, rule: KdlNode, idx: int) -> Adw.ActionRow:
        match_node = rule.get_child("match")
        ns = match_node.props.get("namespace", "") if match_node else ""
        actions = [c.name for c in rule.children if c.name != "match"]
        row = Adw.ActionRow(
            title=GLib.markup_escape_text(f"namespace={ns}" if ns else "(any)"),
            subtitle=GLib.markup_escape_text(", ".join(actions[:4])),
        )
        del_btn = Gtk.Button(icon_name="user-trash-symbolic")
        del_btn.set_valign(Gtk.Align.CENTER)
        del_btn.add_css_class("flat")
        del_btn.add_css_class("error")
        del_btn.connect("clicked", lambda *_, i=idx: self._on_delete_layer(i))
        row.add_suffix(del_btn)
        return row

    def _on_add_layer(self, *_):
        self._show_layer_dialog(None, -1)

    def _on_delete_layer(self, idx: int):
        rules = self._get_layer_rules()
        if 0 <= idx < len(rules):
            self._nodes.remove(rules[idx])
            self._commit("remove layer rule")
            self._rebuild_layer()

    def _show_layer_dialog(self, rule: KdlNode | None, idx: int):
        LAYER_BOOL_ACTIONS = [
            "place-within-backdrop",
            "block-out-from-screencast",
        ]
        dialog = Adw.Dialog(title="Layer Rule")
        dialog.set_content_width(440)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        hdr = Adw.HeaderBar()
        hdr.set_title_widget(Adw.WindowTitle(title="Layer Rule"))
        box.append(hdr)

        prefs = Adw.PreferencesPage()
        prefs.set_vexpand(True)

        match_grp = Adw.PreferencesGroup(title="Match")
        match_node = rule.get_child("match") if rule else None
        ns_entry = Adw.EntryRow(title="Namespace (regex, e.g. ^waybar$)")
        ns_entry.set_text(
            str(match_node.props.get("namespace", "")) if match_node else ""
        )
        match_grp.add(ns_entry)
        prefs.add(match_grp)

        act_grp = Adw.PreferencesGroup(title="Actions")
        bool_rows: dict[str, Adw.SwitchRow] = {}
        for a in LAYER_BOOL_ACTIONS:
            sr = Adw.SwitchRow(title=a)
            sr.set_active(rule.get_child(a) is not None if rule else False)
            act_grp.add(sr)
            bool_rows[a] = sr

        opacity_adj = Gtk.Adjustment(
            value=1.0, lower=0.0, upper=1.0, step_increment=0.05
        )
        if rule:
            op_node = rule.get_child("opacity")
            if op_node and op_node.args:
                opacity_adj.set_value(float(op_node.args[0]))
        opacity_row = Adw.SpinRow(title="Opacity", adjustment=opacity_adj, digits=2)
        act_grp.add(opacity_row)
        prefs.add(act_grp)
        box.append(prefs)

        save_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        save_box.set_halign(Gtk.Align.END)
        save_box.set_margin_start(16)
        save_box.set_margin_end(16)
        save_box.set_margin_bottom(16)
        save_btn = Gtk.Button(label="Save Rule")
        save_btn.add_css_class("suggested-action")
        save_btn.add_css_class("pill")

        def _save(*_):
            new_rule = KdlNode("layer-rule")
            ns = ns_entry.get_text().strip()
            if ns:
                from nirimod.kdl_parser import KdlRawString

                m = KdlNode("match")
                m.props["namespace"] = KdlRawString(ns)
                new_rule.children.append(m)
            for a, sr in bool_rows.items():
                if sr.get_active():
                    cn = KdlNode(a)
                    cn.args = [True]
                    new_rule.children.append(cn)
            op_val = opacity_row.get_value()
            if op_val < 1.0:
                op_node = KdlNode("opacity")
                op_node.args = [round(op_val, 2)]
                new_rule.children.append(op_node)
            rules = self._get_layer_rules()
            if idx >= 0 and 0 <= idx < len(rules):
                i = self._nodes.index(rules[idx])
                self._nodes[i] = new_rule
            else:
                self._nodes.append(new_rule)
            self._commit("layer rule")
            self._rebuild_layer()
            dialog.close()

        save_btn.connect("clicked", _save)
        save_box.append(save_btn)
        box.append(save_box)
        dialog.set_child(box)
        dialog.present(self._win)

    def _get_rules(self) -> list[KdlNode]:
        return [n for n in self._nodes if n.name == "window-rule"]

    def _rebuild(self):
        parent = self._rules_grp.get_parent()
        if parent is None:
            return
        rules = self._get_rules()
        new_grp = Adw.PreferencesGroup(
            title="Window Rules", description=f"{len(rules)} window rule(s)"
        )
        for i, rule in enumerate(rules):
            row = self._make_rule_row(rule, i)
            new_grp.add(row)
        parent.remove(self._rules_grp)
        parent.append(new_grp)
        self._rules_grp = new_grp

    def _make_rule_row(self, rule: KdlNode, idx: int) -> Adw.ActionRow:

        matches = []
        for c in rule.children:
            if c.name == "match":
                parts = []
                for k, v in c.props.items():
                    parts.append(f"{k}={v}")
                for a in c.args:
                    parts.append(str(a))
                matches.append(" ".join(parts))
        match_str = ", ".join(matches) if matches else "(global)"

        actions = [c.name for c in rule.children if c.name != "match"]
        action_str = ", ".join(actions[:4])

        row = Adw.ActionRow(
            title=GLib.markup_escape_text(match_str),
            subtitle=GLib.markup_escape_text(action_str),
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
        self._show_rule_dialog(None, -1)

    def _on_edit(self, idx: int):
        rules = self._get_rules()
        if 0 <= idx < len(rules):
            self._show_rule_dialog(rules[idx], idx)

    def _on_delete(self, idx: int):
        rules = self._get_rules()
        if 0 <= idx < len(rules):
            self._nodes.remove(rules[idx])
            self._commit("remove window rule")
            self._rebuild()

    def _show_rule_dialog(self, rule: KdlNode | None, rule_idx: int):
        dialog = Adw.Dialog(title="Window Rule")
        dialog.set_content_width(500)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        hdr = Adw.HeaderBar()
        hdr.set_title_widget(Adw.WindowTitle(title="Window Rule"))
        box.append(hdr)

        prefs = Adw.PreferencesPage()
        prefs.set_vexpand(True)

        match_grp = Adw.PreferencesGroup(title="Match Criteria")
        match_entries: dict[str, Adw.EntryRow] = {}
        match_node = rule.get_child("match") if rule else None

        for field in STR_MATCH_FIELDS:
            e = Adw.EntryRow(title=field)
            val = match_node.props.get(field, "") if match_node else ""
            e.set_text(str(val))
            match_grp.add(e)
            match_entries[field] = e

        match_bool_rows: dict[str, Adw.SwitchRow] = {}
        for field in BOOL_MATCH_FIELDS:
            sr = Adw.SwitchRow(title=field)
            val = match_node.props.get(field, False) if match_node else False
            sr.set_active(bool(val))
            match_grp.add(sr)
            match_bool_rows[field] = sr
        prefs.add(match_grp)

        act_grp = Adw.PreferencesGroup(title="Actions")
        bool_rows: dict[str, Adw.SwitchRow] = {}
        for a in BOOL_ACTIONS:
            sr = Adw.SwitchRow(title=a)
            sr.set_active(rule.get_child(a) is not None if rule else False)
            act_grp.add(sr)
            bool_rows[a] = sr

        num_rows: dict[str, Adw.SpinRow] = {}
        for a in NUM_ACTIONS:
            max_v = 1.0 if a == "opacity" else 7680
            step = 0.05 if a == "opacity" else 1
            digits = 2 if a == "opacity" else 0
            cur = 0
            if rule:
                cn = rule.get_child(a)
                cur = cn.args[0] if cn and cn.args else 0
            adj = Gtk.Adjustment(
                value=float(cur), lower=0, upper=max_v, step_increment=step
            )
            sr = Adw.SpinRow(title=a, adjustment=adj, digits=digits)
            act_grp.add(sr)
            num_rows[a] = sr

        str_rows: dict[str, Adw.EntryRow] = {}
        for a in STR_ACTIONS:
            e = Adw.EntryRow(title=a)
            if rule:
                cn = rule.get_child(a)
                e.set_text(str(cn.args[0]) if cn and cn.args else "")
            act_grp.add(e)
            str_rows[a] = e

        prefs.add(act_grp)
        box.append(prefs)

        save_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        save_box.set_halign(Gtk.Align.END)
        save_box.set_margin_start(16)
        save_box.set_margin_end(16)
        save_box.set_margin_bottom(16)
        save_btn = Gtk.Button(label="Save Rule")
        save_btn.add_css_class("suggested-action")
        save_btn.add_css_class("pill")

        def _save(*_):
            new_rule = KdlNode("window-rule")

            match_node_new = KdlNode("match")
            has_match = False
            for f, e in match_entries.items():
                v = e.get_text().strip()
                if v:
                    from nirimod.kdl_parser import KdlRawString

                    match_node_new.props[f] = KdlRawString(v)
                    has_match = True
            for f, sr in match_bool_rows.items():
                if sr.get_active():
                    match_node_new.props[f] = True
                    has_match = True
            if has_match:
                new_rule.children.append(match_node_new)

            for a, sr in bool_rows.items():
                if sr.get_active():
                    cn = KdlNode(a)
                    cn.args = [True]
                    new_rule.children.append(cn)

            for a, sr in num_rows.items():
                v = sr.get_value()
                if v > 0:
                    cn = KdlNode(a)
                    cn.args = [v if a == "opacity" else int(v)]
                    new_rule.children.append(cn)

            for a, e in str_rows.items():
                v = e.get_text().strip()
                if v:
                    cn = KdlNode(a)
                    cn.args = [v]
                    new_rule.children.append(cn)

            if rule_idx >= 0:
                rules = self._get_rules()
                if 0 <= rule_idx < len(rules):
                    idx_in_nodes = self._nodes.index(rules[rule_idx])
                    self._nodes[idx_in_nodes] = new_rule
            else:
                self._nodes.append(new_rule)

            self._commit("window rule")
            self._rebuild()
            dialog.close()

        save_btn.connect("clicked", _save)
        save_box.append(save_btn)
        box.append(save_box)

        dialog.set_child(box)
        dialog.present(self._win)
