"""Window Rules page — MangoWM windowrule / layerrule."""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk, GLib

from mangomod.mango_config import parse_kv_rule, build_kv_rule
from mangomod.pages.base import BasePage

BOOL_OPTIONS = [
    ("isfloating", "Floating"),
    ("isfullscreen", "Fullscreen"),
    ("noblur", "Disable Blur"),
    ("isopensilent", "Open Silent (no focus)"),
    ("force_maximize", "Force Maximize"),
    ("isnoborder", "No Border"),
    ("isnoshadow", "No Shadow"),
    ("isglobal", "Global (all tags)"),
]

NUM_OPTIONS = [
    ("width", "Width (px)", 0, 7680),
    ("height", "Height (px)", 0, 7680),
]

STR_OPTIONS = [
    ("monitor", "Monitor", "DP-1"),
    ("tags", "Tags", "1 2 3"),
]


class WindowRulesPage(BasePage):
    def __init__(self, window):
        super().__init__(window)
        self._win_rows: list[Gtk.Widget] = []
        self._layer_rows: list[Gtk.Widget] = []

    def build(self):
        tb, _, _, content = self._make_toolbar_page("Window Rules")
        self._content = content

        self._win_grp = Adw.PreferencesGroup(title="Window Rules")
        add = Gtk.Button(icon_name="list-add-symbolic")
        add.set_tooltip_text("Add window rule")
        add.add_css_class("flat")
        add.add_css_class("circular")
        add.connect("clicked", lambda *_: self._show_dialog(None, -1))
        self._win_grp.set_header_suffix(add)
        content.append(self._win_grp)

        self._layer_grp = Adw.PreferencesGroup(
            title="Layer Rules",
            description="Rules for layer-shell surfaces (bars, overlays, wallpapers)",
        )
        add_l = Gtk.Button(icon_name="list-add-symbolic")
        add_l.set_tooltip_text("Add layer rule")
        add_l.add_css_class("flat")
        add_l.add_css_class("circular")
        add_l.connect("clicked", lambda *_: self._show_layer_dialog(None, -1))
        self._layer_grp.set_header_suffix(add_l)
        content.append(self._layer_grp)

        self.refresh()
        return tb

    def refresh(self):
        self._rebuild()
        self._rebuild_layer()

    # ── Window rules ────────────────────────────────────────────────

    def _rules(self) -> list[str]:
        return self._config.get_all("windowrule")

    def _rebuild(self):
        for r in self._win_rows:
            self._win_grp.remove(r)
        self._win_rows.clear()

        rules = self._rules()
        self._win_grp.set_description(f"{len(rules)} rule(s) — click to edit")
        for i, rule in enumerate(rules):
            row = self._make_row(rule, i)
            self._win_grp.add(row)
            self._win_rows.append(row)

    def _make_row(self, rule: str, idx: int) -> Adw.ActionRow:
        parts = parse_kv_rule(rule)
        bits = []
        for k in ("name", "appid", "title"):
            if k in parts:
                bits.append(f"{k}: {parts[k]}")
        title = " • ".join(bits) or rule
        subtitle = ", ".join(
            f"{k}:{v}" for k, v in parts.items()
            if k not in ("name", "appid", "title")
        ) or "no actions"

        row = Adw.ActionRow(
            title=GLib.markup_escape_text(title),
            subtitle=GLib.markup_escape_text(subtitle),
        )
        row.set_activatable(True)
        row.add_css_class("monospace")

        d = Gtk.Button(icon_name="user-trash-symbolic")
        d.set_valign(Gtk.Align.CENTER)
        d.add_css_class("flat")
        d.add_css_class("error")
        d.connect("clicked", lambda *_, i=idx: self._on_delete(i))
        row.add_suffix(d)
        row.connect("activated", lambda *_, r=rule, i=idx: self._show_dialog(r, i))
        return row

    def _on_delete(self, idx):
        if 0 <= idx < len(self._rules()):
            self._config.remove_nth("windowrule", idx)
            self._commit("remove window rule")
            self._rebuild()

    def _show_dialog(self, rule: str | None, idx: int):
        parts = parse_kv_rule(rule) if rule else {}
        dialog = Adw.Dialog(title="Edit Window Rule" if rule else "New Window Rule")
        dialog.set_content_width(500)
        dialog.set_content_height(620)

        tv = Adw.ToolbarView()
        hdr = Adw.HeaderBar()
        hdr.set_title_widget(Adw.WindowTitle(title=dialog.get_title()))
        tv.add_top_bar(hdr)

        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        prefs = Adw.PreferencesPage()

        # Match
        match_grp = Adw.PreferencesGroup(title="Match Criteria")
        name_row = Adw.EntryRow(title="Rule Name (label, optional)")
        name_row.set_text(parts.get("name", ""))
        match_grp.add(name_row)
        appid_row = Adw.EntryRow(title="App ID (regex, e.g. ^kitty$)")
        appid_row.set_text(parts.get("appid", ""))
        match_grp.add(appid_row)
        title_row = Adw.EntryRow(title="Window Title (regex)")
        title_row.set_text(parts.get("title", ""))
        match_grp.add(title_row)
        prefs.add(match_grp)

        # Actions — booleans
        act_grp = Adw.PreferencesGroup(title="Actions")
        bool_rows: dict[str, Adw.SwitchRow] = {}
        for key, label in BOOL_OPTIONS:
            sr = Adw.SwitchRow(title=label)
            val = parts.get(key, "0")
            sr.set_active(val in ("1", "true", "yes"))
            act_grp.add(sr)
            bool_rows[key] = sr
        prefs.add(act_grp)

        # Numeric
        num_grp = Adw.PreferencesGroup(title="Dimensions")
        num_rows: dict[str, Adw.SpinRow] = {}
        for key, label, lo, hi in NUM_OPTIONS:
            try:
                cur = int(parts.get(key, "0"))
            except ValueError:
                cur = 0
            adj = Gtk.Adjustment(value=cur, lower=lo, upper=hi, step_increment=10)
            sr = Adw.SpinRow(title=label, adjustment=adj, digits=0)
            num_grp.add(sr)
            num_rows[key] = sr
        prefs.add(num_grp)

        # Strings
        str_grp = Adw.PreferencesGroup(title="Placement")
        str_rows: dict[str, Adw.EntryRow] = {}
        for key, label, ph in STR_OPTIONS:
            e = Adw.EntryRow(title=label)
            e.set_text(parts.get(key, ""))
            e.set_tooltip_text(f"e.g. {ph}")
            str_grp.add(e)
            str_rows[key] = e
        prefs.add(str_grp)

        scroll.set_child(prefs)
        tv.set_content(scroll)

        # Save bar
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

        save = Gtk.Button(label="Save Rule")
        save.add_css_class("suggested-action")
        save.add_css_class("pill")
        bar.append(save)
        tv.add_bottom_bar(bar)

        def _save(*_):
            new_parts: dict[str, str] = {}
            name = name_row.get_text().strip()
            if name:
                new_parts["name"] = name
            appid = appid_row.get_text().strip()
            if appid:
                new_parts["appid"] = appid
            title = title_row.get_text().strip()
            if title:
                new_parts["title"] = title

            for key, sr in bool_rows.items():
                if sr.get_active():
                    new_parts[key] = "1"
            for key, sr in num_rows.items():
                v = int(sr.get_value())
                if v > 0:
                    new_parts[key] = str(v)
            for key, e in str_rows.items():
                v = e.get_text().strip()
                if v:
                    new_parts[key] = v

            new_rule = build_kv_rule(new_parts)
            rules = self._rules()
            if idx >= 0 and 0 <= idx < len(rules):
                self._config.replace_nth("windowrule", idx, new_rule)
            else:
                self._config.add("windowrule", new_rule)
            self._commit("window rule")
            self._rebuild()
            dialog.close()

        save.connect("clicked", _save)
        dialog.set_child(tv)
        dialog.present(self._win)

    # ── Layer rules ─────────────────────────────────────────────────

    def _layer_rules(self) -> list[str]:
        return self._config.get_all("layerrule")

    def _rebuild_layer(self):
        for r in self._layer_rows:
            self._layer_grp.remove(r)
        self._layer_rows.clear()

        rules = self._layer_rules()
        self._layer_grp.set_description(f"{len(rules)} rule(s) — layer surfaces")
        for i, rule in enumerate(rules):
            row = self._make_layer_row(rule, i)
            self._layer_grp.add(row)
            self._layer_rows.append(row)

    def _make_layer_row(self, rule: str, idx: int) -> Adw.ActionRow:
        parts = parse_kv_rule(rule)
        ns = parts.get("namespace", "(any)")
        subtitle = ", ".join(
            f"{k}:{v}" for k, v in parts.items() if k != "namespace"
        ) or "no actions"

        row = Adw.ActionRow(title=f"namespace: {ns}", subtitle=subtitle)
        row.set_activatable(True)
        row.add_css_class("monospace")

        d = Gtk.Button(icon_name="user-trash-symbolic")
        d.set_valign(Gtk.Align.CENTER)
        d.add_css_class("flat")
        d.add_css_class("error")
        d.connect("clicked", lambda *_, i=idx: self._on_delete_layer(i))
        row.add_suffix(d)
        row.connect("activated", lambda *_, r=rule, i=idx: self._show_layer_dialog(r, i))
        return row

    def _on_delete_layer(self, idx):
        if 0 <= idx < len(self._layer_rules()):
            self._config.remove_nth("layerrule", idx)
            self._commit("remove layer rule")
            self._rebuild_layer()

    def _show_layer_dialog(self, rule: str | None, idx: int):
        parts = parse_kv_rule(rule) if rule else {}
        dialog = Adw.Dialog(title="Edit Layer Rule" if rule else "New Layer Rule")
        dialog.set_content_width(440)

        tv = Adw.ToolbarView()
        hdr = Adw.HeaderBar()
        hdr.set_title_widget(Adw.WindowTitle(title=dialog.get_title()))
        tv.add_top_bar(hdr)

        prefs = Adw.PreferencesPage()

        match_grp = Adw.PreferencesGroup(title="Match")
        ns_row = Adw.EntryRow(title="Namespace (regex, e.g. ^waybar$)")
        ns_row.set_text(parts.get("namespace", ""))
        match_grp.add(ns_row)
        prefs.add(match_grp)

        act_grp = Adw.PreferencesGroup(title="Actions")
        noblur_row = Adw.SwitchRow(title="Disable Blur")
        noblur_row.set_active(parts.get("noblur", "0") in ("1", "true", "yes"))
        act_grp.add(noblur_row)

        noanim_row = Adw.SwitchRow(title="Disable Animations")
        noanim_row.set_active(parts.get("noanim", "0") in ("1", "true", "yes"))
        act_grp.add(noanim_row)

        ignorealpha_row = Adw.SwitchRow(title="Ignore Alpha for Input")
        ignorealpha_row.set_active(parts.get("ignorealpha", "0") in ("1", "true", "yes"))
        act_grp.add(ignorealpha_row)

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

        save = Gtk.Button(label="Save Rule")
        save.add_css_class("suggested-action")
        save.add_css_class("pill")
        bar.append(save)
        tv.add_bottom_bar(bar)

        def _save(*_):
            new_parts: dict[str, str] = {}
            ns = ns_row.get_text().strip()
            if ns:
                new_parts["namespace"] = ns
            if noblur_row.get_active():
                new_parts["noblur"] = "1"
            if noanim_row.get_active():
                new_parts["noanim"] = "1"
            if ignorealpha_row.get_active():
                new_parts["ignorealpha"] = "1"

            new_rule = build_kv_rule(new_parts)
            rules = self._layer_rules()
            if idx >= 0 and 0 <= idx < len(rules):
                self._config.replace_nth("layerrule", idx, new_rule)
            else:
                self._config.add("layerrule", new_rule)
            self._commit("layer rule")
            self._rebuild_layer()
            dialog.close()

        save.connect("clicked", _save)
        dialog.set_child(tv)
        dialog.present(self._win)
