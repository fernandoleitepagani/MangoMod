

from __future__ import annotations

from typing import TYPE_CHECKING

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("Gio", "2.0")

from gi.repository import Adw, Gtk, Gio

if TYPE_CHECKING:
    from nirimod.window import NiriModWindow


def make_toolbar_page(
    title: str,
    window=None,
) -> tuple[Adw.ToolbarView, Adw.HeaderBar, Gtk.ScrolledWindow, Gtk.Box]:
    tb = Adw.ToolbarView()
    header = Adw.HeaderBar()
    header.set_title_widget(Adw.WindowTitle(title=title))
    tb.add_top_bar(header)

    # Hamburger menu on the content header (appears next to window close button)
    if window is not None:
        menu = Gio.Menu()
        menu.append("Profiles", "win.open_profiles")
        menu.append("Preferences", "win.open_preferences")
        menu_btn = Gtk.MenuButton(icon_name="open-menu-symbolic")
        menu_btn.set_tooltip_text("Menu")
        menu_btn.add_css_class("flat")
        menu_btn.set_menu_model(menu)
        header.pack_end(menu_btn)

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

    def _make_toolbar_page(
        self, title: str
    ) -> tuple[Adw.ToolbarView, Adw.HeaderBar, Gtk.ScrolledWindow, Gtk.Box]:
        return make_toolbar_page(title, window=self._win)

    @property
    def _nodes(self):
        return self._win.get_nodes()

    def _commit(self, description: str = "change"):
        app_state = self._win.app_state
        after = app_state.write_current_kdl()
        
        before = app_state.undo.last_snapshot
        if before is None:
            before = app_state.saved_kdl
            
        if before != after:
            self._win.push_undo(description, before, after)
            
        if after == app_state.saved_kdl:
            self._win.mark_clean()
        else:
            self._win.mark_dirty()

    def build(self) -> Gtk.Widget:
        raise NotImplementedError

    def refresh(self):
        pass

    def on_shown(self):
        pass

    def show_toast(self, msg: str, timeout: int = 3):
        self._win.show_toast(msg, timeout)
