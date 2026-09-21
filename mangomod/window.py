"""Main application window."""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, Gio, GLib, Gtk

from mangomod import mango_config, mango_ipc
from mangomod.state import AppState
from mangomod.theme import CSS

# Below this logical-pixel width the sidebar collapses into an overlay.
COLLAPSE_THRESHOLD_PX = 720

SIDEBAR_GROUPS = [
    ("Input", [
        ("input", "input-keyboard-symbolic", "Input"),
        ("bindings", "preferences-desktop-keyboard-shortcuts-symbolic", "Key Bindings"),
    ]),
    ("Display", [
        ("outputs", "video-display-symbolic", "Outputs"),
        ("appearance", "preferences-desktop-appearance-symbolic", "Appearance"),
        ("animations", "applications-multimedia-symbolic", "Animations"),
    ]),
    ("Workspace", [
        ("layout", "view-grid-symbolic", "Layout"),
        ("window_rules", "preferences-system-symbolic", "Window Rules"),
    ]),
    ("System", [
        ("startup", "system-run-symbolic", "Startup"),
        ("environment", "preferences-other-symbolic", "Environment"),
        ("gestures", "input-touchpad-symbolic", "Gestures & Misc"),
    ]),
    ("Advanced", [("raw_config", "text-x-generic-symbolic", "Raw Config")]),
]

SIDEBAR_PAGES = [e for _, group in SIDEBAR_GROUPS for e in group]


class MangoModWindow(Adw.ApplicationWindow):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_title("MangoMod")
        self.set_default_size(1060, 720)
        self.set_size_request(360, 400)

        # Explicit CSD state. Defaults are already True, but setting them
        # ensures MangoWM's decoration negotiation sees a definite answer.
        self.set_decorated(True)
        self.set_resizable(True)

        self.app_state = AppState()
        self.app_state.load()

        self._current_page_id = ""
        self._pages: dict[str, Gtk.Widget] = {}
        self._sidebar_rows: dict[str, Gtk.ListBoxRow] = {}
        self._sidebar_listboxes: dict[str, Gtk.ListBox] = {}
        self._sidebar_toggle_buttons: list[Gtk.Button] = []

        self._load_css()
        self._build_ui()
        self._setup_breakpoints()

    def _load_css(self):
        p = Gtk.CssProvider()
        p.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), p, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    def _build_ui(self):
        self._toast_overlay = Adw.ToastOverlay()
        self.set_content(self._toast_overlay)

        self._split_view = Adw.OverlaySplitView()
        self._split_view.set_vexpand(True)
        self._split_view.set_collapsed(False)
        self._split_view.set_show_sidebar(True)
        self._split_view.set_pin_sidebar(False)
        self._split_view.set_min_sidebar_width(220)
        self._split_view.set_max_sidebar_width(320)
        self._split_view.set_sidebar_width_fraction(0.25)
        self._toast_overlay.set_child(self._split_view)

        self._split_view.set_sidebar(self._build_sidebar_nav())
        self._split_view.set_content(self._build_content_nav())

        self._setup_shortcuts()
        if SIDEBAR_PAGES:
            self._select_page(SIDEBAR_PAGES[0][0])

    def _setup_breakpoints(self):
        """Auto-collapse the sidebar below COLLAPSE_THRESHOLD_PX.

        Breakpoints only touch `collapsed`. `show-sidebar` is left to the
        user (via the toggle button) so the sidebar doesn't spontaneously
        reappear after the user hides it.
        """
        collapse_bp = Adw.Breakpoint.new(
            Adw.BreakpointCondition.parse(f"max-width: {COLLAPSE_THRESHOLD_PX}px")
        )
        collapse_bp.add_setter(self._split_view, "collapsed", True)
        self.add_breakpoint(collapse_bp)

        pin_bp = Adw.Breakpoint.new(
            Adw.BreakpointCondition.parse(f"min-width: {COLLAPSE_THRESHOLD_PX + 1}px")
        )
        pin_bp.add_setter(self._split_view, "collapsed", False)
        self.add_breakpoint(pin_bp)

    def register_sidebar_toggle(self, btn: Gtk.Button):
        """Called by make_toolbar_page() on every page.

        Button is always visible. Clicking it toggles `show-sidebar`, which
        works in both pinned and collapsed modes.
        """
        self._sidebar_toggle_buttons.append(btn)
        btn.set_visible(True)

    def _build_sidebar_nav(self):
        nav = Adw.NavigationPage(title="MangoMod")

        # The sidebar page's direct child must be an Adw.ToolbarView.
        # libadwaita uses this structure to locate the CSD titlebar and
        # set up client-side resize edges. Wrapping the content in a plain
        # Gtk.Box instead breaks both the titlebar discovery and the
        # resize-edge allocation on some compositors, including MangoWM.
        sidebar_toolbar = Adw.ToolbarView()

        hdr = Adw.HeaderBar()
        hdr.set_title_widget(Adw.WindowTitle(title="MangoMod"))
        sidebar_toolbar.add_top_bar(hdr)

        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_vexpand(True)

        nav_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        nav_box.set_margin_top(8)
        nav_box.set_margin_bottom(16)

        for title, pages in SIDEBAR_GROUPS:
            lbl = Gtk.Label(label=title.upper())
            lbl.set_xalign(0.0)
            lbl.set_margin_start(16)
            lbl.set_margin_end(16)
            lbl.set_margin_top(16)
            lbl.set_margin_bottom(4)
            lbl.add_css_class("nm-sidebar-section-label")
            nav_box.append(lbl)

            lb = Gtk.ListBox()
            lb.set_selection_mode(Gtk.SelectionMode.SINGLE)
            lb.add_css_class("navigation-sidebar")
            lb.add_css_class("nm-sidebar-listbox")
            lb.set_margin_start(8)
            lb.set_margin_end(8)
            lb.connect("row-selected", self._on_row_selected)

            for pid, icon, label in pages:
                row = self._make_sidebar_row(pid, icon, label)
                lb.append(row)
                self._sidebar_rows[pid] = row
                self._sidebar_listboxes[pid] = lb
            nav_box.append(lb)

        scroll.set_child(nav_box)
        sidebar_toolbar.set_content(scroll)
        nav.set_child(sidebar_toolbar)
        return nav

    def _make_sidebar_row(self, pid, icon, label):
        row = Gtk.ListBoxRow()
        row.page_id = pid
        b = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        b.set_margin_start(6)
        b.set_margin_end(6)
        b.set_margin_top(4)
        b.set_margin_bottom(4)
        img = Gtk.Image(icon_name=icon)
        img.add_css_class("nm-sidebar-icon")
        b.append(img)
        lbl = Gtk.Label(label=label, xalign=0)
        lbl.set_hexpand(True)
        b.append(lbl)
        row.set_child(b)
        return row

    def _build_content_nav(self):
        self._content_nav = Adw.NavigationPage(title="")

        # The content side already contains Adw.ToolbarView widgets (one per
        # page), so the direct child can be a plain box. libadwaita walks
        # into the stack to find the visible page's headerbar.
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        self._banner = Gtk.Label(
            label="MangoWM is not running — changes will be saved but not applied live",
            xalign=0,
        )
        self._banner.add_css_class("nm-mango-banner")
        self._banner.set_visible(not self.app_state.mango_running)
        root.append(self._banner)

        self._stack = Gtk.Stack()
        self._stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self._stack.set_transition_duration(120)
        self._stack.set_vexpand(True)
        root.append(self._stack)

        self._build_all_pages()

        self._dirty_bar = self._build_dirty_bar()
        root.append(self._dirty_bar)
        self._content_nav.set_child(root)
        return self._content_nav

    def _build_dirty_bar(self):
        bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        bar.add_css_class("nm-dirty-bar")
        bar.set_visible(False)
        bar.set_margin_start(12)
        bar.set_margin_end(12)
        bar.set_margin_top(6)
        bar.set_margin_bottom(6)

        self._dirty_label = Gtk.Label(label="Unsaved changes")
        self._dirty_label.set_hexpand(True)
        self._dirty_label.set_xalign(0.0)
        self._dirty_label.set_opacity(0.7)
        bar.append(self._dirty_label)

        d = Gtk.Button(label="Discard")
        d.add_css_class("destructive-action")
        d.add_css_class("flat")
        d.connect("clicked", lambda *_: self._on_discard())
        bar.append(d)

        s = Gtk.Button(label="Save & Apply")
        s.add_css_class("suggested-action")
        s.connect("clicked", lambda *_: self._on_save())
        bar.append(s)
        return bar

    def _build_all_pages(self):
        from mangomod.pages import (
            outputs, input_page, layout, appearance, animations,
            bindings, window_rules, startup, environment, gestures, raw_config,
        )
        builders = {
            "outputs": outputs.OutputsPage,
            "input": input_page.InputPage,
            "layout": layout.LayoutPage,
            "appearance": appearance.AppearancePage,
            "animations": animations.AnimationsPage,
            "bindings": bindings.BindingsPage,
            "window_rules": window_rules.WindowRulesPage,
            "startup": startup.StartupPage,
            "environment": environment.EnvironmentPage,
            "gestures": gestures.GesturesPage,
            "raw_config": raw_config.RawConfigPage,
        }
        for pid, _, _ in SIDEBAR_PAGES:
            cls = builders.get(pid)
            if cls:
                obj = cls(window=self)
                w = obj.build()
                self._pages[pid] = obj
                self._stack.add_named(w, pid)

    # ── Sidebar toggle ──────────────────────────────────────────────

    def _toggle_sidebar(self, *_):
        """Toggle sidebar visibility. Works in both pinned and collapsed modes."""
        self._split_view.set_show_sidebar(
            not self._split_view.get_show_sidebar()
        )

    def _hide_sidebar(self, *_):
        """Only auto-hide after page selection in collapsed/overlay mode."""
        if self._split_view.get_collapsed():
            self._split_view.set_show_sidebar(False)

    # ── Sidebar / page selection ────────────────────────────────────

    def _on_row_selected(self, _lb, row):
        if row is None:
            return
        pid = getattr(row, "page_id", None)
        if pid:
            for opid, lb in self._sidebar_listboxes.items():
                if lb is not _lb:
                    lb.unselect_all()
            self._select_page(pid)

    def _select_page(self, pid):
        self._current_page_id = pid
        self._stack.set_visible_child_name(pid)
        for p, _, title in SIDEBAR_PAGES:
            if p == pid:
                self._content_nav.set_title(title)
                break
        for p, lb in self._sidebar_listboxes.items():
            r = self._sidebar_rows.get(p)
            if r and p == pid:
                lb.select_row(r)
        self._hide_sidebar()
        page = self._pages.get(pid)
        if page and hasattr(page, "on_shown"):
            page.on_shown()

    def _setup_shortcuts(self):
        app = self.get_application()
        if not app:
            return
        a = Gio.SimpleAction.new("save", None)
        a.connect("activate", lambda *_: self._on_save())
        self.add_action(a)
        app.set_accels_for_action("win.save", ["<Control>s"])

        p = Gio.SimpleAction.new("open_preferences", None)
        p.connect("activate", lambda *_: self._open_preferences())
        self.add_action(p)

        toggle = Gio.SimpleAction.new("toggle-sidebar", None)
        toggle.connect("activate", lambda *_: self._toggle_sidebar())
        self.add_action(toggle)
        app.set_accels_for_action("win.toggle-sidebar", ["F9", "<Control>b"])

        esc = Gio.SimpleAction.new("close-sidebar", None)
        esc.connect("activate", lambda *_: self._hide_sidebar())
        self.add_action(esc)
        app.set_accels_for_action("win.close-sidebar", ["Escape"])

    def get_config(self):
        return self.app_state.config

    def mark_dirty(self):
        self.app_state.mark_dirty()
        self._dirty_bar.set_visible(True)

    def mark_clean(self):
        self.app_state.mark_clean()
        self._dirty_bar.set_visible(False)

    def notify_config_changed(self):
        self.app_state.load()
        page = self._pages.get(self._current_page_id)
        if page and hasattr(page, "refresh"):
            page.refresh()

    def _on_save(self):
        disk_snapshot = self.app_state.disk_snapshot()
        self.app_state.write_to_path()
        new_snapshot = self.app_state.snapshot()

        def _on_validated(result):
            ok, msg = result
            if not ok:
                self.app_state.restore_disk(disk_snapshot)
                self.show_validation_error(msg)
                return
            mango_ipc.run_in_thread(mango_ipc.reload, _finish_save)

        def _finish_save(reload_result):
            ok, msg = reload_result
            self.app_state.commit_save(new_snapshot)
            for pid in ("outputs", "raw_config"):
                p = self._pages.get(pid)
                if p and hasattr(p, "refresh"):
                    p.refresh()
            self.mark_clean()
            if ok:
                self.show_toast("Config saved and applied", timeout=3)
            else:
                self.show_toast(f"Config saved, but reload failed: {msg}", timeout=8)

        mango_ipc.run_in_thread(
            lambda: mango_ipc.validate_config(str(mango_config.MANGO_CONFIG)),
            _on_validated,
        )

    def show_validation_error(self, msg):
        dialog = Adw.AlertDialog(
            heading="Configuration Validation Failed",
            body="MangoWM rejected the configuration syntax:",
        )
        dialog.add_response("close", "Close")
        dialog.add_response("raw", "Open in Raw Config")
        dialog.set_response_appearance("raw", Adw.ResponseAppearance.SUGGESTED)

        scroll = Gtk.ScrolledWindow()
        scroll.set_min_content_height(160)
        scroll.set_max_content_height(360)
        tv = Gtk.TextView()
        tv.set_editable(False)
        tv.set_monospace(True)
        tv.get_buffer().set_text(msg)
        scroll.set_child(tv)
        dialog.set_extra_child(scroll)

        def _on_response(_d, response):
            if response == "raw":
                self._select_page("raw_config")

        dialog.choose(self, None, _on_response)

    def _on_discard(self):
        self.app_state.discard()
        self.mark_clean()
        self.notify_config_changed()

    def show_toast(self, message, timeout=3):
        self._toast_overlay.add_toast(Adw.Toast(title=message, timeout=timeout))

    def _open_preferences(self):
        from mangomod import app_settings

        w = Adw.PreferencesWindow()
        w.set_title("MangoMod Preferences")
        w.set_modal(True)
        w.set_transient_for(self)
        w.set_default_size(500, 300)

        page = Adw.PreferencesPage(title="General", icon_name="emblem-system-symbolic")
        grp = Adw.PreferencesGroup(title="Configuration File")

        row = Adw.ActionRow(title="Config Path")
        cur = app_settings.get("config_path", "")
        row.set_subtitle(cur if cur else "Default (~/.config/mango/config.conf)")

        b = Gtk.Button(label="Browse...")
        b.set_valign(Gtk.Align.CENTER)
        b.connect("clicked", lambda _b: self._on_browse_config(w, row))
        row.add_suffix(b)

        c = Gtk.Button(icon_name="edit-clear-symbolic")
        c.set_valign(Gtk.Align.CENTER)
        c.connect("clicked", lambda _b: self._on_clear_config(row))
        row.add_suffix(c)

        grp.add(row)
        page.add(grp)
        w.add(page)
        w.present()

    def _on_browse_config(self, parent, row):
        from mangomod import app_settings
        d = Gtk.FileDialog()
        d.set_title("Select Mango Config")
        f = Gtk.FileFilter()
        f.set_name("Config files")
        f.add_pattern("*.conf")
        filters = Gio.ListStore.new(Gtk.FileFilter)
        filters.append(f)
        d.set_filters(filters)

        def _on_response(dlg, result):
            try:
                file = dlg.open_finish(result)
                if file:
                    path = file.get_path()
                    app_settings.set("config_path", path)
                    row.set_subtitle(path)
                    self.show_toast("Restart MangoMod to use the new config path.", timeout=5)
            except GLib.Error:
                pass

        d.open(parent, None, _on_response)

    def _on_clear_config(self, row):
        from mangomod import app_settings
        app_settings.set("config_path", "")
        row.set_subtitle("Default (~/.config/mango/config.conf)")
        self.show_toast("Restart MangoMod to use the default config path.", timeout=5)
