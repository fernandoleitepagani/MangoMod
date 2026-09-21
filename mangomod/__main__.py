"""MangoMod application entry point."""

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
    sys.exit(1)

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gio, GLib

from mangomod.window import MangoModWindow


class MangoModApp(Adw.Application):
    def __init__(self):
        super().__init__(
            application_id="io.github.mangomod",
            flags=Gio.ApplicationFlags.NON_UNIQUE,
        )
        GLib.set_application_name("MangoMod")
        GLib.set_prgname("mangomod")

        Adw.StyleManager.get_default().set_color_scheme(Adw.ColorScheme.FORCE_DARK)

        self._cli_config_path: str | None = None
        self.add_main_option(
            "config", ord("c"), GLib.OptionFlags.NONE, GLib.OptionArg.STRING,
            "Path to MangoWM configuration file", "PATH",
        )
        self.add_main_option(
            "version", ord("v"), GLib.OptionFlags.NONE, GLib.OptionArg.NONE,
            "Show application version", None,
        )

    def do_handle_local_options(self, options: GLib.VariantDict) -> int:
        if options.contains("version"):
            print("MangoMod 0.6.0")
            return 0
        if options.contains("config"):
            self._cli_config_path = options.lookup_value("config").get_string()
        return -1

    def do_activate(self):
        win = self.get_active_window()
        if win is None:
            from mangomod import app_settings
            from mangomod.mango_config import set_paths

            cfg_path = self._cli_config_path or app_settings.get("config_path", "")
            set_paths(config_path=cfg_path)
            win = MangoModWindow(application=self)
        win.present()


def main():
    app = MangoModApp()
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
