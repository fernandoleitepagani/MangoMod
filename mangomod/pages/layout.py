"""Layout page — MangoWM flat gaps, window sizes, and tag layouts."""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk

from mangomod.mango_config import parse_kv_rule, build_kv_rule
from mangomod.pages.base import BasePage

GAP_KEYS = [
    ("gappih", "Inner Horizontal Gap"),
    ("gappiv", "Inner Vertical Gap"),
    ("gappoh", "Outer Horizontal Gap"),
    ("gappov", "Outer Vertical Gap"),
]

# MangoWM layout names accepted by tagrule=id:N,layout_name:X
MANGO_LAYOUTS = [
    "tile",
    "dwindle",
    "scroller",
    "spiral",
    "monocle",
    "grid",
    "floating",
]


class LayoutPage(BasePage):
    def __init__(self, window):
        super().__init__(window)
        self._tag_rows: list[Adw.ComboRow] = []
        self._tag_count_guard = False

    def build(self):
        tb, _, _, content = self._make_toolbar_page("Layout")
        self._content = content
        self._build_content()
        return tb

    def _build_content(self):
        content = self._content

        # ── General (window sizing) ────────────────────────────────
        gen = Adw.PreferencesGroup(
            title="General",
            description="Default split ratios for each layout type",
        )

        self._add_float_row(
            gen, "default_mfact", "Default Master Factor",
            default=0.5,
            subtitle="Width ratio of the master pane in tile layout",
        )
        self._add_float_row(
            gen, "dwindle_split_ratio", "Dwindle Split Ratio",
            default=0.5,
            subtitle="Split ratio for dwindle layout",
        )
        self._add_float_row(
            gen, "scroller_default_proportion", "Scroller Default Proportion",
            default=0.8,
            subtitle="Default column width in scroller layout",
        )
        self._add_str_row(
            gen, "scroller_proportion_preset", "Scroller Proportion Presets",
            placeholder="0.5,0.8,1.0",
            subtitle="Comma-separated proportions cycled by keybind",
        )
        content.append(gen)

        # ── Gaps ───────────────────────────────────────────────────
        gaps = Adw.PreferencesGroup(
            title="Window Gaps (px)",
            description="MangoWM uses inner/outer gaps split by axis",
        )
        for key, label in GAP_KEYS:
            try:
                val = int(self._config.get(key, "0"))
            except (TypeError, ValueError):
                val = 0
            adj = Gtk.Adjustment(value=val, lower=0, upper=500, step_increment=1)
            row = Adw.SpinRow(title=label, adjustment=adj, digits=0)
            row._last_val = val

            def _on_changed(r, _, k=key):
                nv = int(r.get_value())
                if nv != getattr(r, "_last_val", None):
                    r._last_val = nv
                    self._set(k, nv)

            row.connect("notify::value", _on_changed)
            gaps.add(row)
        content.append(gaps)

        # ── Tags ───────────────────────────────────────────────────
        tag_grp = Adw.PreferencesGroup(
            title="Tags",
            description="Number of workspaces and each tag's default layout",
        )

        try:
            tag_num = int(self._config.get("tag_num", "9"))
        except (TypeError, ValueError):
            tag_num = 9
        tag_num = max(1, min(tag_num, 32))

        tag_count_adj = Gtk.Adjustment(
            value=tag_num, lower=1, upper=32, step_increment=1,
        )
        tag_count_row = Adw.SpinRow(
            title="Number of Tags",
            subtitle="Total workspaces tracked by view/tagsilent binds",
            adjustment=tag_count_adj,
            digits=0,
        )
        tag_count_row._last_val = tag_num

        def _on_tag_count_changed(r, _, grp=tag_grp):
            if self._tag_count_guard:
                return
            nv = int(r.get_value())
            if nv == getattr(r, "_last_val", None):
                return
            r._last_val = nv
            self._set("tag_num", nv)
            self._rebuild_tag_rows(grp, nv)

        tag_count_row.connect("notify::value", _on_tag_count_changed)
        tag_grp.add(tag_count_row)

        self._rebuild_tag_rows(tag_grp, tag_num)
        content.append(tag_grp)

    # ── Tag rows ─────────────────────────────────────────────────────

    def _rebuild_tag_rows(self, grp: Adw.PreferencesGroup, tag_num: int):
        self._tag_count_guard = True
        try:
            for r in self._tag_rows:
                grp.remove(r)
            self._tag_rows.clear()

            for i in range(1, tag_num + 1):
                row = self._make_tag_row(i)
                grp.add(row)
                self._tag_rows.append(row)
        finally:
            self._tag_count_guard = False

    def _make_tag_row(self, tag_id: int) -> Adw.ComboRow:
        current = self._get_tag_layout(tag_id)
        model = Gtk.StringList.new(MANGO_LAYOUTS)
        row = Adw.ComboRow(title=f"Tag {tag_id}", model=model)
        if current in MANGO_LAYOUTS:
            row.set_selected(MANGO_LAYOUTS.index(current))
        else:
            row.set_selected(0)
        row.connect(
            "notify::selected",
            lambda r, _, tid=tag_id: self._set_tag_layout(
                tid, MANGO_LAYOUTS[r.get_selected()]
            ),
        )
        return row

    def _get_tag_layout(self, tag_id: int) -> str:
        for rule in self._config.get_all("tagrule"):
            p = parse_kv_rule(rule)
            if p.get("id") == str(tag_id):
                return p.get("layout_name", "dwindle")
        return "dwindle"

    def _set_tag_layout(self, tag_id: int, layout_name: str):
        # Replace existing tagrule for this tag (preserving its source file)
        ordinal = 0
        for entry in self._config.entries:
            if entry.key == "tagrule":
                p = parse_kv_rule(entry.value)
                if p.get("id") == str(tag_id):
                    p["layout_name"] = layout_name
                    self._config.replace_nth(
                        "tagrule", ordinal, build_kv_rule(p)
                    )
                    self._commit(f"tag {tag_id} layout")
                    return
                ordinal += 1

        # Tag rule doesn't exist yet — add to same file as existing tagrules
        source = self._config.main_path
        for entry in self._config.entries:
            if entry.key == "tagrule":
                source = entry.source
                break
        self._config.add(
            "tagrule", f"id:{tag_id},layout_name:{layout_name}", source=source,
        )
        self._commit(f"tag {tag_id} layout")

    # ── Generic row builders ─────────────────────────────────────────

    def _add_float_row(self, grp, key, title, default, subtitle=None):
        cur = self._config.get(key)
        try:
            val = float(cur) if cur is not None else default
        except (TypeError, ValueError):
            val = default
        adj = Gtk.Adjustment(
            value=val, lower=0.05, upper=1.0, step_increment=0.05,
        )
        row = Adw.SpinRow(title=title, adjustment=adj, digits=2)
        if subtitle:
            row.set_subtitle(subtitle)
        row._last_val = val

        def _on(r, _, k=key):
            nv = round(float(r.get_value()), 2)
            if abs(nv - getattr(r, "_last_val", 0.0)) > 0.001:
                r._last_val = nv
                self._set(k, nv)

        row.connect("notify::value", _on)
        grp.add(row)

    def _add_str_row(self, grp, key, title, placeholder="", subtitle=None):
        cur = self._config.get(key)
        row = Adw.EntryRow(title=title)
        if cur is not None:
            row.set_text(str(cur))
        row.set_show_apply_button(True)
        if placeholder:
            row.set_tooltip_text(f"e.g. {placeholder}")
        elif subtitle:
            row.set_tooltip_text(subtitle)
        row.connect("apply", lambda r, k=key: self._set(k, r.get_text().strip()))
        grp.add(row)

    # ── Config write ─────────────────────────────────────────────────

    def _set(self, key, value):
        if value == "" or value is None:
            self._config.remove(key)
        else:
            self._config.set(key, value)
        self._commit(f"layout {key}")

    def refresh(self):
        for c in list(self._content):
            self._content.remove(c)
        self._build_content()
