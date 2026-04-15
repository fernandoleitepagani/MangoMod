"""Shared base class and helpers for all NiriMod pages."""

from __future__ import annotations

from typing import TYPE_CHECKING

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk

if TYPE_CHECKING:
    from nirimod.window import NiriModWindow


def make_toolbar_page(
    title: str,
) -> tuple[Adw.ToolbarView, Adw.HeaderBar, Gtk.ScrolledWindow, Gtk.Box]:
    tb = Adw.ToolbarView()
    header = Adw.HeaderBar()
    header.set_title_widget(Adw.WindowTitle(title=title))
    tb.add_top_bar(header)

    scroll = Gtk.ScrolledWindow()
    scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
    scroll.set_vexpand(True)

    content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
    content.set_margin_start(32)
    content.set_margin_end(32)
    content.set_margin_top(24)
    content.set_margin_bottom(32)
    scroll.set_child(content)
    tb.set_content(scroll)

    return tb, header, scroll, content


class BasePage:
    def __init__(self, window: "NiriModWindow"):
        self._win = window

    @property
    def _nodes(self):
        return self._win.get_nodes()

    def _commit(self, description: str = "change"):
        """Save nodes and mark dirty after a change."""
        before = self._win.app_state.saved_kdl
        after = self._win.app_state.write_current_kdl()
        self._win.push_undo(description, before, after)
        self._win.mark_dirty()

    def build(self) -> Gtk.Widget:
        raise NotImplementedError

    def refresh(self):
        pass

    def on_shown(self):
        pass

    def show_toast(self, msg: str, timeout: int = 3):
        self._win.show_toast(msg, timeout)
