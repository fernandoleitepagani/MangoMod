from __future__ import annotations

from typing import TYPE_CHECKING

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("Gio", "2.0")
from gi.repository import Adw, Gtk, Gio

if TYPE_CHECKING:
    from mangomod.window import MangoModWindow


def make_toolbar_page(title, window=None):
    tb = Adw.ToolbarView()
    header = Adw.HeaderBar()
    tb.add_top_bar(header)

    if window is not None:
        menu = Gio.Menu()
        menu.append("Preferences", "win.open_preferences")
        btn = Gtk.MenuButton(icon_name="open-menu-symbolic")
        btn.add_css_class("flat")
        btn.set_menu_model(menu)
        header.pack_end(btn)

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


class _SuspendCtx:
    """Context manager: run code with _commit suppressed."""

    def __init__(self, page: "BasePage"):
        self._page = page

    def __enter__(self):
        self._page._suspend_commit = True

    def __exit__(self, *exc):
        self._page._suspend_commit = False
        return False


class BasePage:
    def __init__(self, window: "MangoModWindow"):
        self._win = window
        self._suspend_commit = False

    def _make_toolbar_page(self, title):
        return make_toolbar_page(title, window=self._win)

    @property
    def _config(self):
        return self._win.get_config()

    def _commit(self, description="change"):
        if self._suspend_commit:
            return
        state = self._win.app_state
        state.invalidate_cache()
        if state.is_clean():
            self._win.mark_clean()
        else:
            self._win.mark_dirty()

    def _suspend(self):
        return _SuspendCtx(self)

    def build(self):
        raise NotImplementedError

    def refresh(self):
        pass

    def on_shown(self):
        pass

    def show_toast(self, msg, timeout=3):
        self._win.show_toast(msg, timeout)
