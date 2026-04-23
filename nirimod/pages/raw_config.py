"""Raw Config page — read-only view of the full merged config."""

from __future__ import annotations

import subprocess

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk, GLib, Pango, Gio

from nirimod import niri_ipc
from nirimod.kdl_parser import NIRI_CONFIG
from nirimod.pages.base import BasePage, make_toolbar_page


class RawConfigPage(BasePage):
    def build(self) -> Gtk.Widget:
        tb, header, _, content = self._make_toolbar_page("Raw Config")
        self._content = content
        
        # File selector (replaces the window title)
        self._current_files = []
        self._file_dropdown = Gtk.DropDown()
        self._file_dropdown.set_valign(Gtk.Align.CENTER)
        self._file_dropdown.connect("notify::selected-item", self._on_file_selected)
        
        # Wrap dropdown in a box to act as title widget
        title_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        title_box.set_halign(Gtk.Align.CENTER)
        
        title_label = Gtk.Label(label="<b>File:</b>", use_markup=True)
        title_box.append(title_label)
        title_box.append(self._file_dropdown)
        
        # File selector goes to pack_start
        header.pack_start(title_box)

        # Header Actions
        validate_btn = Gtk.Button(label="Validate")
        validate_btn.add_css_class("suggested-action")
        validate_btn.connect("clicked", self._on_validate)
        header.pack_end(validate_btn)
        

        copy_btn = Gtk.Button(icon_name="edit-copy-symbolic", tooltip_text="Copy")
        copy_btn.connect("clicked", self._on_copy)
        header.pack_end(copy_btn)

        refresh_btn = Gtk.Button(icon_name="view-refresh-symbolic", tooltip_text="Refresh")
        refresh_btn.connect("clicked", lambda *_: self.refresh())
        header.pack_end(refresh_btn)

        # Code Editor View
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
        scroll2.add_css_class("card") # Make the editor look like a card
        scroll2.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroll2.set_vexpand(True)
        scroll2.set_hexpand(True)
        scroll2.set_child(self._textview)
        content.append(scroll2)

        self.refresh()
        return tb

    def refresh(self):
        state = self._win.app_state

        if state.is_multi_file:
            self._current_files = sorted(list(state.source_files))
            if NIRI_CONFIG in self._current_files:
                self._current_files.remove(NIRI_CONFIG)
                self._current_files.insert(0, NIRI_CONFIG)
        else:
            self._current_files = [NIRI_CONFIG]

        strings = [p.name for p in self._current_files]
        self._file_dropdown.set_model(Gtk.StringList.new(strings))
        
        self._load_selected_file()

    def _on_file_selected(self, dropdown, param):
        self._load_selected_file()

    def _load_selected_file(self):
        idx = self._file_dropdown.get_selected()
        if idx == Gtk.INVALID_LIST_POSITION or idx >= len(self._current_files):
            return

        path = self._current_files[idx]
        text = path.read_text() if path.exists() else f"// File not found: {path}"
        
        buf = self._textview.get_buffer()
        buf.set_text(text)
        self._apply_syntax_highlighting(buf, text)

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

    def _on_copy(self, *_):
        buf = self._textview.get_buffer()
        text = buf.get_text(buf.get_start_iter(), buf.get_end_iter(), False)
        cb = self._textview.get_clipboard()
        cb.set(text)
        self.show_toast("Config copied to clipboard", timeout=2)

    def _on_validate(self, *_):
        self.show_toast("Validating...")

        def _on_validated(result):
            ok, msg = result
            self.show_toast(msg[:120], timeout=5)

        niri_ipc.run_in_thread(
            lambda: niri_ipc.validate_config(str(NIRI_CONFIG)), _on_validated
        )
