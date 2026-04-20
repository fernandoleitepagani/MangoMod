"""Keyboard input page."""

from __future__ import annotations


import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk

from nirimod.kdl_parser import (
    KdlNode,
    find_or_create,
    set_child_arg,
    set_node_flag,
    safe_switch_connect,
)
from nirimod.pages.base import BasePage, make_toolbar_page


class KeyboardPage(BasePage):
    def build(self) -> Gtk.Widget:
        tb, _, _, content = self._make_toolbar_page("Keyboard")
        self._content = content
        self._build_content()
        return tb

    def _build_content(self):
        content = self._content
        nodes = self._nodes

        kb_node = find_or_create(nodes, "input", "keyboard")
        xkb_node = kb_node.get_child("xkb") or KdlNode("xkb")

        xkb_grp = Adw.PreferencesGroup(title="XKB Options")
        xkb_grp.set_description("Set these to override system keyboard settings")

        fields = [
            ("layout", "Layout", "e.g. us,ru"),
            ("variant", "Variant", "e.g. dvorak"),
            ("model", "Model", ""),
            ("options", "Options", "e.g. grp:win_space_toggle"),
            ("rules", "Rules", ""),
        ]
        self._xkb_entries: dict[str, Adw.EntryRow] = {}
        for key, title, ph in fields:
            row = Adw.EntryRow(title=title)
            row.set_show_apply_button(True)
            val = xkb_node.child_arg(key) if xkb_node else None
            if val:
                row.set_text(str(val))
            row.set_input_purpose(Gtk.InputPurpose.FREE_FORM)
            row.connect("apply", lambda r, k=key: self._set_xkb(k, r.get_text()))
            xkb_grp.add(row)
            self._xkb_entries[key] = row
        content.append(xkb_grp)

        repeat_grp = Adw.PreferencesGroup(title="Key Repeat")
        delay_adj = Gtk.Adjustment(
            value=kb_node.child_arg("repeat-delay") or 600,
            lower=100,
            upper=3000,
            step_increment=50,
        )
        delay_row = Adw.SpinRow(
            title="Repeat Delay (ms)", adjustment=delay_adj, digits=0
        )
        delay_row.connect(
            "notify::value",
            lambda r, _: self._set_kb("repeat-delay", int(r.get_value())),
        )

        rate_adj = Gtk.Adjustment(
            value=kb_node.child_arg("repeat-rate") or 25,
            lower=1,
            upper=200,
            step_increment=1,
        )
        rate_row = Adw.SpinRow(
            title="Repeat Rate (keys/sec)", adjustment=rate_adj, digits=0
        )
        rate_row.connect(
            "notify::value",
            lambda r, _: self._set_kb("repeat-rate", int(r.get_value())),
        )
        repeat_grp.add(delay_row)
        repeat_grp.add(rate_row)
        content.append(repeat_grp)

        misc_grp = Adw.PreferencesGroup(title="Misc")
        numlock_row = Adw.SwitchRow(title="Enable Num Lock on Startup")
        nl_init = kb_node.get_child("numlock") is not None
        numlock_row.set_active(nl_init)
        safe_switch_connect(numlock_row, nl_init, self._toggle_numlock)
        misc_grp.add(numlock_row)
        content.append(misc_grp)

    def _get_kb_node(self):
        return find_or_create(self._nodes, "input", "keyboard")

    def _get_xkb_node(self):
        kb = self._get_kb_node()
        xkb = kb.get_child("xkb")
        if xkb is None:
            xkb = KdlNode("xkb")
            kb.children.insert(0, xkb)
        return xkb

    def _set_xkb(self, key: str, value: str):
        xkb = self._get_xkb_node()
        if value.strip():
            set_child_arg(xkb, key, value.strip())
        else:
            from nirimod.kdl_parser import remove_child

            remove_child(xkb, key)
        self._commit(f"keyboard xkb {key}")

    def _set_kb(self, key: str, value):
        kb = self._get_kb_node()
        set_child_arg(kb, key, value)
        self._commit(f"keyboard {key}")

    def _toggle_numlock(self, enabled: bool):
        kb = self._get_kb_node()
        set_node_flag(kb, "numlock", enabled)
        self._commit("keyboard numlock")

    def refresh(self):
        for child in list(self._content):
            self._content.remove(child)
        self._build_content()
