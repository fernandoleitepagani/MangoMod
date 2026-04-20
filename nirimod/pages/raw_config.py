"""Raw Config page — read-only view of the full merged config."""

from __future__ import annotations

import subprocess

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, GLib, Pango

from nirimod import niri_ipc
from nirimod.kdl_parser import NIRI_CONFIG
from nirimod.pages.base import BasePage, make_toolbar_page


class RawConfigPage(BasePage):
    def build(self) -> Gtk.Widget:
        tb, header, _, content = self._make_toolbar_page("Raw Config")
        self._content = content
        
        # Action Bar
        action_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        action_bar.set_margin_bottom(16)
        
        # Validate button
        validate_btn = Gtk.Button(label="Validate", icon_name="emblem-ok-symbolic")
        validate_btn.add_css_class("pill")
        validate_btn.add_css_class("suggested-action")
        validate_btn.connect("clicked", self._on_validate)
        action_bar.append(validate_btn)
        
        # Open in Editor button
        open_btn = Gtk.Button(label="Open Editor", icon_name="document-open-symbolic")
        open_btn.add_css_class("pill")
        open_btn.connect("clicked", self._on_open_editor)
        action_bar.append(open_btn)
        
        # Refresh button
        refresh_btn = Gtk.Button(icon_name="view-refresh-symbolic")
        refresh_btn.add_css_class("pill")
        refresh_btn.set_tooltip_text("Reload config from disk")
        refresh_btn.connect("clicked", lambda *_: self.refresh())
        action_bar.append(refresh_btn)
        
        # Copy button
        copy_btn = Gtk.Button(icon_name="edit-copy-symbolic")
        copy_btn.add_css_class("pill")
        copy_btn.set_tooltip_text("Copy to clipboard")
        copy_btn.connect("clicked", self._on_copy)
        action_bar.append(copy_btn)

        # Status spacer
        action_bar.append(Gtk.Box(hexpand=True))

        self._status_lbl = Gtk.Label(label="")
        self._status_lbl.set_xalign(1.0)
        self._status_lbl.add_css_class("dim-label")
        action_bar.append(self._status_lbl)

        content.append(action_bar)

        self._textview = Gtk.TextView()
        self._textview.set_editable(False)
        self._textview.set_monospace(True)
        self._textview.set_wrap_mode(Gtk.WrapMode.NONE)
        self._textview.set_left_margin(16)
        self._textview.set_right_margin(16)
        self._textview.set_top_margin(16)
        self._textview.set_bottom_margin(16)
        self._textview.add_css_class("code-editor")

        scroll2 = Gtk.ScrolledWindow()
        scroll2.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroll2.set_vexpand(True)
        scroll2.set_hexpand(True)
        scroll2.set_child(self._textview)
        content.append(scroll2)

        self.refresh()
        return tb

    def refresh(self):
        path = NIRI_CONFIG

        if path.exists():
            text = path.read_text()
        else:
            text = f"// File not found: {path}"

        buf = self._textview.get_buffer()
        buf.set_text(text)
        self._apply_syntax_highlighting(buf, text)
        self._status_lbl.set_label(str(path))

    def _apply_syntax_highlighting(self, buf: Gtk.TextBuffer, text: str):
        """Simple KDL syntax highlighting using text tags."""
        # Create tags if not already
        tag_table = buf.get_tag_table()

        def _get_or_create_tag(name, **props):
            t = tag_table.lookup(name)
            if t is None:
                t = buf.create_tag(name, **props)
            return t

        comment_tag = _get_or_create_tag(
            "comment", foreground="#6a9955", style=Pango.Style.ITALIC
        )
        string_tag = _get_or_create_tag("string", foreground="#ce9178")
        node_tag = _get_or_create_tag("node", foreground="#9cdcfe")
        keyword_tag = _get_or_create_tag("keyword", foreground="#c586c0")

        import re

        def _apply(pattern, tag, group=0):
            for m in re.finditer(pattern, text, re.MULTILINE):
                s = buf.get_iter_at_offset(m.start(group))
                e = buf.get_iter_at_offset(m.end(group))
                buf.apply_tag(tag, s, e)

        _apply(r"//[^\n]*", comment_tag)
        _apply(r'"[^"\\]*(?:\\.[^"\\]*)*"', string_tag)
        _apply(r"\b(true|false|null)\b", keyword_tag)
        _apply(r"^(\s*)([a-zA-Z][\w\-]*)", node_tag, group=2)

    def _on_open_editor(self, *_):
        try:
            subprocess.Popen(["xdg-open", str(NIRI_CONFIG)])
        except Exception as e:
            self.show_toast(f"Failed to open editor: {e}")

    def _on_copy(self, *_):
        buf = self._textview.get_buffer()
        text = buf.get_text(buf.get_start_iter(), buf.get_end_iter(), False)
        cb = self._textview.get_clipboard()
        cb.set_text(text)
        self.show_toast("Config copied to clipboard", timeout=2)

    def _on_validate(self, *_):
        self._status_lbl.set_label("Validating...")

        def _on_validated(result):
            ok, msg = result
            if ok:
                self._status_lbl.set_markup(
                    '<span color="#4caf50">✓  Config is valid</span>'
                )
            else:
                self._status_lbl.set_markup(
                    f'<span color="#f44336">✗  {GLib.markup_escape_text(msg)}</span>'
                )
            self.show_toast(msg[:120], timeout=5)

        niri_ipc.run_in_thread(
            lambda: niri_ipc.validate_config(str(NIRI_CONFIG)), _on_validated
        )
