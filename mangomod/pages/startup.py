"""Startup Programs page — MangoWM exec-once / exec."""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk, GLib

from mangomod.pages.base import BasePage

class StartupPage(BasePage):
    def build(self):
        tb, _, _, content = self._make_toolbar_page("Startup Programs")
        self._content = content
        self.refresh()
        return tb

    def refresh(self):
        while True:
            c = self._content.get_first_child()
            if c is None:
                break
            self._content.remove(c)

        entries = self._entries()

        if not entries:
            status = Adw.StatusPage(
                title="No Startup Programs",
                description="Programs added here launch automatically when MangoWM starts.",
                icon_name="applications-system-symbolic",
            )
            add = Gtk.Button(label="Add Program")
            add.add_css_class("pill")
            add.add_css_class("suggested-action")
            add.set_halign(Gtk.Align.CENTER)
            add.connect("clicked", self._on_add)

            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
            box.set_valign(Gtk.Align.CENTER)
            box.set_vexpand(True)
            box.append(status)
            box.append(add)
            self._content.append(box)
        else:
            grp = Adw.PreferencesGroup(
                title="Startup Programs",
                description=f"{len(entries)} program{'s' if len(entries) != 1 else ''} configured",
            )
            with self._suspend():
                for i, (k, v) in enumerate(entries):
                    grp.add(self._make_row(k, v, i))
            self._content.append(grp)

            add = Gtk.Button(label="Add Another Program")
            add.add_css_class("pill")
            add.set_halign(Gtk.Align.CENTER)
            add.set_margin_top(16)
            add.connect("clicked", self._on_add)
            self._content.append(add)

    def _entries(self) -> list[tuple[str, str]]:
        return [
            (k, v) for k, v in self._config.get_all_keyed()
            if k in ("exec-once", "exec")
        ]

    def _make_row(self, kind: str, cmd: str, idx: int) -> Adw.ActionRow:
        display = GLib.markup_escape_text(cmd) or "(empty)"
        subtitle = (
            "Runs every reload (exec)"
            if kind == "exec"
            else "Runs once at startup (exec-once)"
        )
        row = Adw.ActionRow(title=display, subtitle=subtitle)
        row.set_activatable(True)
        row.connect("activated", lambda *_, i=idx: self._on_edit(i))

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
        e = self._entries()
        if 0 <= idx < len(e):
            self._show_dialog(e[idx], idx)

    def _on_delete(self, idx):
        e = self._entries()
        if 0 <= idx < len(e):
            kind, _val = e[idx]
            kind_ordinal = sum(
                1 for i, (k, _v) in enumerate(e) if k == kind and i < idx
            )
            self._config.remove_nth(kind, kind_ordinal)
            self._commit("remove startup entry")
            GLib.idle_add(self._deferred_refresh)

    def _deferred_refresh(self):
        self.refresh()
        return False

    def _show_dialog(self, entry, idx):
        dialog = Adw.AlertDialog(
            heading="Startup Program",
            body="Command runs at MangoWM startup.",
        )
        cmd_row = Adw.EntryRow(title="Command")
        reload_switch = Adw.SwitchRow(
            title="Run on every reload",
            subtitle="exec= runs on every config reload; exec-once= only at startup",
        )

        if entry:
            kind, cmd = entry
            cmd_row.set_text(cmd)
            reload_switch.set_active(kind == "exec")

        grp = Adw.PreferencesGroup()
        grp.add(cmd_row)
        grp.add(reload_switch)
        dialog.set_extra_child(grp)

        dialog.add_response("cancel", "Cancel")
        dialog.add_response("save", "Save")
        dialog.set_response_appearance("save", Adw.ResponseAppearance.SUGGESTED)

        def _on_resp(d, r):
            if r != "save":
                return
            cmd = cmd_row.get_text().strip()
            if not cmd:
                return
            kind = "exec" if reload_switch.get_active() else "exec-once"

            e = self._entries()
            if 0 <= idx < len(e):
                old_kind, _old_val = e[idx]
                ordinal = sum(
                    1 for i, (k, _v) in enumerate(e)
                    if k == old_kind and i < idx
                )
                if old_kind == kind:
                    self._config.replace_nth(kind, ordinal, cmd)
                else:
                    self._config.replace_nth(old_kind, ordinal, cmd, new_key=kind)
            else:
                self._config.add(kind, cmd)

            self._commit("startup entry")
            GLib.idle_add(self._deferred_refresh)

        dialog.connect("response", _on_resp)
        dialog.present(self._win)
