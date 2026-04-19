"""NiriMod application entry point."""

from __future__ import annotations

import sys

try:
    import gi
except ModuleNotFoundError:
    print(
        "\033[31mError: Could not find Python GObject bindings (PyGObject).\033[0m",
        file=sys.stderr,
    )
    print(
        "This application requires system-level libraries to interface with GTK4.",
        file=sys.stderr,
    )
    print(
        "\nPlease install the required packages for your distribution:", file=sys.stderr
    )
    print(
        "  \033[1mArch:\033[0m   sudo pacman -S python-gobject gtk4 libadwaita",
        file=sys.stderr,
    )
    print(
        "  \033[1mFedora:\033[0m sudo dnf install python3-gobject gtk4 libadwaita",
        file=sys.stderr,
    )
    print(
        "  \033[1mUbuntu:\033[0m sudo apt install python3-gi gir1.2-gtk-4.0 gir1.2-adw-1",
        file=sys.stderr,
    )
    print(
        "\nAfter installing, re-run the installer or re-create your virtual environment.",
        file=sys.stderr,
    )
    sys.exit(1)

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gio, GLib, Gtk

from nirimod.window import NiriModWindow


class NiriModApp(Adw.Application):
    def __init__(self):
        super().__init__(
            application_id="io.github.nirimod",
            flags=Gio.ApplicationFlags.NON_UNIQUE,
        )
        GLib.set_application_name("NiriMod")
        GLib.set_prgname("nirimod")

        # Suppress Adwaita-WARNING about mixed system dark mode settings
        settings = Gtk.Settings.get_default()
        if settings:
            settings.set_property("gtk-application-prefer-dark-theme", False)

        # Prefer dark theme globally via libadwaita
        style_manager = Adw.StyleManager.get_default()
        style_manager.set_color_scheme(Adw.ColorScheme.PREFER_DARK)

    def do_activate(self):
        win = self.get_active_window()
        if win is None:
            win = NiriModWindow(application=self)
        win.present()


def main():
    app = NiriModApp()
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
