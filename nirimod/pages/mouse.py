"""Mouse & Touchpad input page."""

from __future__ import annotations


import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk

from nirimod import niri_ipc
from nirimod.kdl_parser import (
    KdlNode,
    find_or_create,
    set_child_arg,
    set_node_flag,
    safe_switch_connect,
)
from nirimod.pages.base import BasePage, make_toolbar_page


ACCEL_PROFILES = ["default", "flat", "adaptive"]
SCROLL_METHODS_TP = ["two-finger", "edge", "on-button-down", "no-scroll"]
SCROLL_METHODS_M = ["no-scroll", "two-finger", "on-button-down"]
TAP_BUTTON_MAPS = ["left-right-middle", "left-middle-right"]
CLICK_METHODS = ["button-areas", "clickfinger"]


class MousePage(BasePage):
    def build(self) -> Gtk.Widget:
        tb, _, _, content = make_toolbar_page("Mouse & Touchpad")
        self._content = content
        self._build_content()
        return tb

    def _build_content(self):
        content = self._content
        nodes = self._nodes

        ffm_grp = Adw.PreferencesGroup(title="Focus")
        input_node = find_or_create(nodes, "input")

        ffm_row = Adw.SwitchRow(title="Focus Follows Mouse")
        ffm_node = input_node.get_child("focus-follows-mouse")
        ffm_row._last_active = ffm_node is not None
        ffm_row.set_active(ffm_node is not None)

        def _on_ffm_toggled(r, _):
            new_val = r.get_active()
            if new_val != getattr(r, "_last_active", None):
                r._last_active = new_val
                self._toggle_ffm(new_val)

        ffm_row.connect("notify::active", _on_ffm_toggled)
        ffm_grp.add(ffm_row)

        scroll_val = getattr(self, "_last_scroll_val", 33)
        if ffm_node:
            vRaw = ffm_node.props.get("max-scroll-amount")
            if vRaw is not None:
                if isinstance(vRaw, int):
                    scroll_val = vRaw
                elif isinstance(vRaw, str):
                    vClean = vRaw.replace("%", "").strip()
                    try:
                        scroll_val = int(float(vClean)) if vClean else 33
                    except ValueError:
                        pass

        self._last_scroll_val = scroll_val

        scroll_adj = Gtk.Adjustment(
            value=scroll_val, lower=0, upper=100, step_increment=1
        )
        scroll_pct_row = Adw.SpinRow(
            title="Max Scroll Amount (%)",
            subtitle="0% = only fully visible windows",
            adjustment=scroll_adj,
            digits=0,
        )
        scroll_pct_row.set_sensitive(ffm_node is not None)
        self._scroll_pct_row = scroll_pct_row

        scroll_pct_row._last_val = scroll_val

        def _on_scroll_pct_changed(r, _):
            new_val = int(r.get_value())
            if new_val != getattr(r, "_last_val", None):
                r._last_val = new_val
                self._set_ffm_scroll(new_val)

        scroll_pct_row.connect("notify::value", _on_scroll_pct_changed)
        ffm_grp.add(scroll_pct_row)

        warp_row = Adw.SwitchRow(title="Warp Mouse to Focus")
        warp_init = input_node.get_child("warp-mouse-to-focus") is not None
        warp_row.set_active(warp_init)
        safe_switch_connect(
            warp_row,
            warp_init,
            lambda enabled: self._toggle_input_flag("warp-mouse-to-focus", enabled),
        )
        ffm_grp.add(warp_row)
        content.append(ffm_grp)

        tp_grp = Adw.PreferencesGroup(title="Touchpad")
        has_tp = niri_ipc.has_touchpad()
        if not has_tp:
            tp_grp.set_description("No touchpad detected")
            tp_grp.set_sensitive(False)

        tp_node = find_or_create(nodes, "input", "touchpad")

        def tp_switch(key, label, subtitle=""):
            r = Adw.SwitchRow(title=label, subtitle=subtitle)
            ini = tp_node.get_child(key) is not None
            r.set_active(ini)
            safe_switch_connect(
                r, ini, lambda enabled, k=key: self._set_tp_flag(k, enabled)
            )
            return r

        tp_grp.add(tp_switch("tap", "Tap to Click"))
        tp_grp.add(tp_switch("dwt", "Disable While Typing"))
        tp_grp.add(tp_switch("dwtp", "Disable While Trackpointing"))
        tp_grp.add(tp_switch("natural-scroll", "Natural Scroll"))
        tp_grp.add(tp_switch("drag", "Tap Drag"))
        tp_grp.add(tp_switch("drag-lock", "Tap Drag Lock"))
        tp_grp.add(tp_switch("disabled-on-external-mouse", "Disable on External Mouse"))

        spd = tp_node.child_arg("accel-speed") or 0.0
        spd_adj = Gtk.Adjustment(
            value=float(spd), lower=-1.0, upper=1.0, step_increment=0.05
        )
        spd_row = Adw.SpinRow(title="Accel Speed", adjustment=spd_adj, digits=2)
        spd_row.connect(
            "notify::value", lambda r, _: self._set_tp("accel-speed", r.get_value())
        )
        tp_grp.add(spd_row)

        ap_model = Gtk.StringList.new(ACCEL_PROFILES)
        ap_row = Adw.ComboRow(title="Accel Profile", model=ap_model)
        cur_ap = tp_node.child_arg("accel-profile") or "default"
        if cur_ap in ACCEL_PROFILES:
            ap_row.set_selected(ACCEL_PROFILES.index(cur_ap))
        ap_row.connect(
            "notify::selected",
            lambda r, _: self._set_tp(
                "accel-profile", ACCEL_PROFILES[r.get_selected()]
            ),
        )
        tp_grp.add(ap_row)

        sm_model = Gtk.StringList.new(SCROLL_METHODS_TP)
        sm_row = Adw.ComboRow(title="Scroll Method", model=sm_model)
        cur_sm = tp_node.child_arg("scroll-method") or "two-finger"
        if cur_sm in SCROLL_METHODS_TP:
            sm_row.set_selected(SCROLL_METHODS_TP.index(cur_sm))
        sm_row.connect(
            "notify::selected",
            lambda r, _: self._set_tp(
                "scroll-method", SCROLL_METHODS_TP[r.get_selected()]
            ),
        )
        tp_grp.add(sm_row)

        cm_model = Gtk.StringList.new(CLICK_METHODS)
        cm_row = Adw.ComboRow(title="Click Method", model=cm_model)
        cur_cm = tp_node.child_arg("click-method") or "button-areas"
        if cur_cm in CLICK_METHODS:
            cm_row.set_selected(CLICK_METHODS.index(cur_cm))
        cm_row.connect(
            "notify::selected",
            lambda r, _: self._set_tp("click-method", CLICK_METHODS[r.get_selected()]),
        )
        tp_grp.add(cm_row)

        content.append(tp_grp)

        m_grp = Adw.PreferencesGroup(title="Mouse")
        m_node = find_or_create(nodes, "input", "mouse")

        m_nat = Adw.SwitchRow(title="Natural Scroll")
        mn_init = m_node.get_child("natural-scroll") is not None
        m_nat.set_active(mn_init)
        safe_switch_connect(
            m_nat, mn_init, lambda enabled: self._set_m_flag("natural-scroll", enabled)
        )
        m_grp.add(m_nat)

        m_spd = m_node.child_arg("accel-speed") or 0.0
        m_spd_adj = Gtk.Adjustment(
            value=float(m_spd), lower=-1.0, upper=1.0, step_increment=0.05
        )
        m_spd_row = Adw.SpinRow(title="Accel Speed", adjustment=m_spd_adj, digits=2)
        m_spd_row.connect(
            "notify::value", lambda r, _: self._set_m("accel-speed", r.get_value())
        )
        m_grp.add(m_spd_row)

        m_ap_model = Gtk.StringList.new(ACCEL_PROFILES)
        m_ap_row = Adw.ComboRow(title="Accel Profile", model=m_ap_model)
        cur_m_ap = m_node.child_arg("accel-profile") or "default"
        if cur_m_ap in ACCEL_PROFILES:
            m_ap_row.set_selected(ACCEL_PROFILES.index(cur_m_ap))
        m_ap_row.connect(
            "notify::selected",
            lambda r, _: self._set_m("accel-profile", ACCEL_PROFILES[r.get_selected()]),
        )
        m_grp.add(m_ap_row)
        content.append(m_grp)

        tr_grp = Adw.PreferencesGroup(title="Trackpoint")
        tr_node = find_or_create(nodes, "input", "trackpoint")

        tr_nat = Adw.SwitchRow(title="Natural Scroll")
        tn_init = tr_node.get_child("natural-scroll") is not None
        tr_nat.set_active(tn_init)
        safe_switch_connect(
            tr_nat,
            tn_init,
            lambda enabled: self._set_tr_flag("natural-scroll", enabled),
        )
        tr_grp.add(tr_nat)

        tr_mid = Adw.SwitchRow(title="Middle Button Emulation")
        tm_init = tr_node.get_child("middle-emulation") is not None
        tr_mid.set_active(tm_init)
        safe_switch_connect(
            tr_mid,
            tm_init,
            lambda enabled: self._set_tr_flag("middle-emulation", enabled),
        )
        tr_grp.add(tr_mid)

        tr_spd = tr_node.child_arg("accel-speed") or 0.0
        tr_spd_adj = Gtk.Adjustment(
            value=float(tr_spd), lower=-1.0, upper=1.0, step_increment=0.05
        )
        tr_spd_row = Adw.SpinRow(title="Accel Speed", adjustment=tr_spd_adj, digits=2)
        tr_spd_row.connect(
            "notify::value", lambda r, _: self._set_tr("accel-speed", r.get_value())
        )
        tr_grp.add(tr_spd_row)

        tr_ap_model = Gtk.StringList.new(ACCEL_PROFILES)
        tr_ap_row = Adw.ComboRow(title="Accel Profile", model=tr_ap_model)
        cur_tr_ap = tr_node.child_arg("accel-profile") or "default"
        if cur_tr_ap in ACCEL_PROFILES:
            tr_ap_row.set_selected(ACCEL_PROFILES.index(cur_tr_ap))
        tr_ap_row.connect(
            "notify::selected",
            lambda r, _: self._set_tr(
                "accel-profile", ACCEL_PROFILES[r.get_selected()]
            ),
        )
        tr_grp.add(tr_ap_row)
        content.append(tr_grp)

        cursor_grp = Adw.PreferencesGroup(title="Cursor")
        cursor_node = next((n for n in nodes if n.name == "cursor"), None)

        size_val = (
            int(cursor_node.child_arg("xcursor-size") or 24) if cursor_node else 24
        )
        size_adj = Gtk.Adjustment(value=size_val, lower=8, upper=256, step_increment=2)
        size_row = Adw.SpinRow(title="Cursor Size (px)", adjustment=size_adj, digits=0)
        size_row.connect(
            "notify::value",
            lambda r, _: self._set_cursor("xcursor-size", int(r.get_value())),
        )
        cursor_grp.add(size_row)

        hide_val = (
            int(cursor_node.child_arg("hide-after-inactive-ms") or 0)
            if cursor_node
            else 0
        )
        hide_adj = Gtk.Adjustment(
            value=hide_val, lower=0, upper=60000, step_increment=500
        )
        hide_row = Adw.SpinRow(
            title="Hide After Inactive (ms)",
            subtitle="0 = never hide",
            adjustment=hide_adj,
            digits=0,
        )
        hide_row.connect(
            "notify::value",
            lambda r, _: self._set_cursor("hide-after-inactive-ms", int(r.get_value())),
        )
        cursor_grp.add(hide_row)

        theme_val = (
            str(cursor_node.child_arg("xcursor-theme") or "") if cursor_node else ""
        )
        theme_row = Adw.EntryRow(title="Cursor Theme (e.g. Adwaita)")
        theme_row.set_text(theme_val)
        theme_row.set_show_apply_button(True)
        theme_row.connect("apply", lambda r: self._set_cursor_theme(r.get_text()))
        cursor_grp.add(theme_row)
        content.append(cursor_grp)

    def _get_input_node(self):
        return find_or_create(self._nodes, "input")

    def _get_tp_node(self):
        return find_or_create(self._nodes, "input", "touchpad")

    def _get_m_node(self):
        return find_or_create(self._nodes, "input", "mouse")

    def _toggle_ffm(self, enabled: bool):
        inp = self._get_input_node()
        existing = inp.get_child("focus-follows-mouse")
        if enabled:
            # Only create a new bare node if there isn't already one.
            # If it exists (possibly with max-scroll-amount props), leave it alone.
            if existing is None:
                new_ffm = KdlNode(name="focus-follows-mouse")
                # Restore user's session preference if we just deleted it recently
                if hasattr(self, "_last_scroll_val"):
                    new_ffm.props["max-scroll-amount"] = f"{self._last_scroll_val}%"
                inp.children.insert(0, new_ffm)
        else:
            # Remove the node entirely (losing props is acceptable on disable).
            if existing is not None:
                inp.children.remove(existing)
        # Keep the scroll row sensitivity in sync with the FFM toggle
        if hasattr(self, "_scroll_pct_row"):
            self._scroll_pct_row.set_sensitive(enabled)
        self._commit("focus-follows-mouse")

    def _set_ffm_scroll(self, pct: int):
        inp = self._get_input_node()
        ffm = inp.get_child("focus-follows-mouse")
        if ffm is None:
            ffm = KdlNode("focus-follows-mouse")
            inp.children.append(ffm)
        ffm.props["max-scroll-amount"] = f"{pct}%"
        self._commit("ffm scroll amount")

    def _toggle_input_flag(self, key: str, enabled: bool):
        inp = self._get_input_node()
        set_node_flag(inp, key, enabled)
        self._commit(f"input {key}")

    def _set_tp_flag(self, key: str, enabled: bool):
        tp = self._get_tp_node()
        set_node_flag(tp, key, enabled)
        self._commit(f"touchpad {key}")

    def _set_tp(self, key: str, value):
        tp = self._get_tp_node()
        set_child_arg(tp, key, value)
        self._commit(f"touchpad {key}")

    def _set_m_flag(self, key: str, enabled: bool):
        m = self._get_m_node()
        set_node_flag(m, key, enabled)
        self._commit(f"mouse {key}")

    def _set_m(self, key: str, value):
        m = self._get_m_node()
        set_child_arg(m, key, value)
        self._commit(f"mouse {key}")

    def _get_tr_node(self):
        return find_or_create(self._nodes, "input", "trackpoint")

    def _set_tr_flag(self, key: str, enabled: bool):
        set_node_flag(self._get_tr_node(), key, enabled)
        self._commit(f"trackpoint {key}")

    def _set_tr(self, key: str, value):
        set_child_arg(self._get_tr_node(), key, value)
        self._commit(f"trackpoint {key}")

    def _get_cursor_node(self):
        from nirimod.kdl_parser import KdlNode as _KN

        existing = next((n for n in self._nodes if n.name == "cursor"), None)
        if existing is None:
            existing = _KN("cursor")
            self._nodes.append(existing)
        return existing

    def _set_cursor(self, key: str, value):
        set_child_arg(self._get_cursor_node(), key, value)
        self._commit(f"cursor {key}")

    def _set_cursor_theme(self, theme: str):
        cur = self._get_cursor_node()
        if theme.strip():
            set_child_arg(cur, "xcursor-theme", theme.strip())
        else:
            from nirimod.kdl_parser import remove_child

            remove_child(cur, "xcursor-theme")
        self._commit("cursor xcursor-theme")

    def refresh(self):
        for child in list(self._content):
            self._content.remove(child)
        self._build_content()
