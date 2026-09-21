"""Raw Config page — file-per-source editor."""

from __future__ import annotations

import re
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, GLib, Pango

from mangomod import mango_ipc
from mangomod.mango_config import MANGO_CONFIG
from mangomod.pages.base import BasePage


class RawConfigPage(BasePage):
    def build(self):
        tb, header, _, content = self._make_toolbar_page("Raw Config")
        self._content = content
        self._buffer_modified = False
        self._original_text = ""
        self._current_files: list[Path] = []

        self._dropdown = Gtk.DropDown()
        self._dropdown.set_valign(Gtk.Align.CENTER)
        self._dropdown.connect("notify::selected-item", self._on_file_selected)

        title_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        title_box.set_halign(Gtk.Align.CENTER)
        title_box.append(Gtk.Label(label="File"))
        title_box.append(self._dropdown)
        header.pack_start(title_box)

        validate_btn = Gtk.Button(label="Validate")
        validate_btn.add_css_class("suggested-action")
        validate_btn.connect("clicked", self._on_validate)
        header.pack_end(validate_btn)

        self._save_btn = Gtk.Button(label="Save")
        self._save_btn.add_css_class("suggested-action")
        self._save_btn.set_sensitive(False)
        self._save_btn.connect("clicked", self._on_save)
        header.pack_end(self._save_btn)

        self._discard_btn = Gtk.Button(label="Discard")
        self._discard_btn.add_css_class("destructive-action")
        self._discard_btn.add_css_class("flat")
        self._discard_btn.set_sensitive(False)
        self._discard_btn.connect("clicked", lambda *_: self.refresh())
        header.pack_end(self._discard_btn)

        self._textview = Gtk.TextView()
        self._textview.set_monospace(True)
        self._textview.set_wrap_mode(Gtk.WrapMode.NONE)
        self._textview.set_left_margin(16)
        self._textview.set_right_margin(16)
        self._textview.set_top_margin(16)
        self._textview.set_bottom_margin(16)
        self._textview.add_css_class("code-editor")
        self._buf = self._textview.get_buffer()
        self._buf.connect("changed", self._on_buffer_changed)

        scroll = Gtk.ScrolledWindow()
        scroll.add_css_class("card")
        scroll.set_vexpand(True)
        scroll.set_hexpand(True)
        scroll.set_child(self._textview)
        content.append(scroll)

        self.refresh()
        return tb

    def refresh(self):
        cfg = self._win.app_state.config
        self._current_files = cfg.all_files()

        names = [p.name for p in self._current_files]
        prev_idx = self._dropdown.get_selected()

        # Block the notify signal while swapping the model so we don't
        # recursively re-enter _load_current during the set_model call.
        self._dropdown.handler_block_by_func(self._on_file_selected)
        try:
            self._dropdown.set_model(Gtk.StringList.new(names))
            target = prev_idx if 0 <= prev_idx < len(names) else 0
            if names:
                self._dropdown.set_selected(target)
        finally:
            self._dropdown.handler_unblock_by_func(self._on_file_selected)

        self._load_current()

    def _current_path(self) -> Path | None:
        idx = self._dropdown.get_selected()
        if 0 <= idx < len(self._current_files):
            return self._current_files[idx]
        return None

    def _load_current(self):
        path = self._current_path()
        if path is None:
            return
        text = path.read_text() if path.exists() else ""
        self._buf.handler_block_by_func(self._on_buffer_changed)
        try:
            self._buf.set_text(text)
            self._original_text = text
            self._apply_highlighting(self._buf, text)
        finally:
            self._buf.handler_unblock_by_func(self._on_buffer_changed)
        self._set_modified(False)

    def _on_file_selected(self, dropdown, _):
        self._load_current()

    def _on_buffer_changed(self, buf):
        text = buf.get_text(buf.get_start_iter(), buf.get_end_iter(), False)
        self._set_modified(text != self._original_text)

    def _set_modified(self, modified):
        self._buffer_modified = modified
        self._save_btn.set_sensitive(modified)
        self._discard_btn.set_sensitive(modified)

    def _on_save(self, *_):
        path = self._current_path()
        if path is None:
            return
        text = self._buf.get_text(
            self._buf.get_start_iter(), self._buf.get_end_iter(), False
        )
        original = path.read_text() if path.exists() else None

        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            path.write_text(text)
        except OSError as e:
            self.show_toast(f"Write error: {e}", timeout=6)
            return

        def _on_validated(result):
            ok, msg = result
            if not ok:
                if original is None:
                    try:
                        path.unlink(missing_ok=True)
                    except OSError:
                        pass
                else:
                    try:
                        path.write_text(original)
                    except OSError:
                        pass
                self._win.show_validation_error(msg)
                return
            self._win.app_state.load()
            self._original_text = text
            self._set_modified(False)
            GLib.idle_add(self._deferred_refresh)
            mango_ipc.run_in_thread(mango_ipc.reload, self._on_reloaded)

        mango_ipc.run_in_thread(
            lambda: mango_ipc.validate_config(str(MANGO_CONFIG)),
            _on_validated,
        )

    def _deferred_refresh(self):
        self.refresh()
        return False

    def _on_reloaded(self, result):
        ok, msg = result
        if ok:
            self.show_toast("Config saved and applied", timeout=3)
        else:
            self.show_toast(f"Saved, but reload failed: {msg[:80]}", timeout=8)

    def _apply_highlighting(self, buf, text):
        tt = buf.get_tag_table()

        def _tag(name, **props):
            t = tt.lookup(name)
            return t if t is not None else buf.create_tag(name, **props)

        comment = _tag("comment", foreground="#6a9955", style=Pango.Style.ITALIC)
        key_t = _tag("key", foreground="#9cdcfe")
        value_t = _tag("value", foreground="#ce9178")

        def _apply(pattern, tag, group=0):
            for m in re.finditer(pattern, text, re.MULTILINE):
                buf.apply_tag(
                    tag,
                    buf.get_iter_at_offset(m.start(group)),
                    buf.get_iter_at_offset(m.end(group)),
                )

        _apply(r"#[^\n]*", comment)
        _apply(r"^([A-Za-z_][\w\-]*)=", key_t, group=1)
        _apply(r"=([^\n#]+)", value_t, group=1)

    def _on_validate(self, *_):
        self.show_toast("Validating...")

        def _on_validated(result):
            ok, msg = result
            if ok:
                self.show_toast(msg or "Configuration is valid", timeout=3)
            else:
                self._win.show_validation_error(msg)

        mango_ipc.run_in_thread(
            lambda: mango_ipc.validate_config(str(MANGO_CONFIG)), _on_validated
        )
