"""Main application window — sidebar + content NavigationSplitView."""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gdk, Gio, GLib, Gtk, Pango

from nirimod import niri_ipc
from nirimod.kdl_parser import NIRI_CONFIG
from nirimod.state import AppState
from nirimod import profiles as prof_mod
from nirimod.theme import CSS

SIDEBAR_PAGES = [
    ("outputs", "video-display-symbolic", "Outputs"),
    ("keyboard", "input-keyboard-symbolic", "Keyboard"),
    ("mouse", "input-mouse-symbolic", "Mouse & Touchpad"),
    ("layout", "view-grid-symbolic", "Layout"),
    ("appearance", "preferences-desktop-appearance-symbolic", "Appearance"),
    ("animations", "applications-multimedia-symbolic", "Animations"),
    ("bindings", "preferences-desktop-keyboard-shortcuts-symbolic", "Key Bindings"),
    ("window_rules", "preferences-system-symbolic", "Window Rules"),
    ("startup", "system-run-symbolic", "Startup Programs"),
    ("workspaces", "view-paged-symbolic", "Workspaces"),
    ("environment", "preferences-other-symbolic", "Environment"),
    ("gestures", "input-touchpad-symbolic", "Gestures & Misc"),
    ("raw_config", "text-x-generic-symbolic", "Raw Config"),
]


class NiriModWindow(Adw.ApplicationWindow):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_title("NiriMod")
        self.set_default_size(1060, 720)

        self.app_state = AppState()
        self.app_state.load()
        self._badges: dict[str, int] = {}
        self._current_page_id = ""
        self._pages: dict[str, Gtk.Widget] = {}
        self._sidebar_rows: dict[str, Gtk.ListBoxRow] = {}
        self._badge_labels: dict[str, Gtk.Label] = {}

        self._load_css()
        self._build_ui()
        self._check_onboarding()

    def _load_css(self):
        provider = Gtk.CssProvider()
        provider.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

    def _build_ui(self):
        self._toast_overlay = Adw.ToastOverlay()
        self.set_content(self._toast_overlay)

        root_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self._toast_overlay.set_child(root_box)

        self._niri_banner = Gtk.Label(
            label="⚠  niri is not running — changes will be saved but not applied live",
            xalign=0,
        )
        self._niri_banner.add_css_class("nm-niri-banner")
        self._niri_banner.set_visible(not self.app_state.niri_running)
        root_box.append(self._niri_banner)

        self._split_view = Adw.NavigationSplitView()
        self._split_view.set_vexpand(True)
        root_box.append(self._split_view)

        self._split_view.set_sidebar(self._build_sidebar_nav())
        self._split_view.set_content(self._build_content_nav())

        self._setup_shortcuts()

        # Navigate to first page
        if SIDEBAR_PAGES:
            self._select_page(SIDEBAR_PAGES[0][0])

    def _build_sidebar_nav(self) -> Adw.NavigationPage:
        nav = Adw.NavigationPage(title="NiriMod")

        sidebar_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        sidebar_box.add_css_class("nm-sidebar-bg")

        # Sidebar header and search
        header = Adw.HeaderBar()
        header.set_title_widget(
            Adw.WindowTitle(title="NiriMod", subtitle="Niri Config")
        )
        sidebar_box.append(header)

        self._search_entry = Gtk.SearchEntry()
        self._search_entry.set_placeholder_text("Search settings…")
        self._search_entry.add_css_class("nm-search-entry")
        self._search_entry.set_margin_start(10)
        self._search_entry.set_margin_end(10)
        self._search_entry.set_margin_top(8)
        self._search_entry.set_margin_bottom(4)
        self._search_entry.connect("search-changed", self._on_search_changed)
        self._search_entry.connect("stop-search", self._on_stop_search)
        sidebar_box.append(self._search_entry)

        self._search_popover = Gtk.Popover()
        self._search_popover.set_parent(self._search_entry)
        self._search_popover.set_position(Gtk.PositionType.BOTTOM)
        self._search_popover.set_has_arrow(False)
        self._search_popover.set_autohide(False)
        # Sizing
        self._search_popover.set_size_request(320, 300)

        pop_scroll = Gtk.ScrolledWindow()
        pop_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        pop_scroll.set_max_content_height(400)
        pop_scroll.set_propagate_natural_height(True)

        self._search_results_listbox = Gtk.ListBox()
        self._search_results_listbox.add_css_class("navigation-sidebar")
        self._search_results_listbox.connect(
            "row-activated", self._on_search_result_activated
        )
        pop_scroll.set_child(self._search_results_listbox)
        self._search_popover.set_child(pop_scroll)

        profile_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        profile_box.set_margin_start(12)
        profile_box.set_margin_end(12)
        profile_box.set_margin_top(6)
        profile_box.set_margin_bottom(2)

        prof_label = Gtk.Label(label="Profile:")
        prof_label.set_opacity(0.6)
        prof_label.set_hexpand(True)
        prof_label.set_xalign(0.0)
        profile_box.append(prof_label)

        self._prof_btn = Gtk.Button(label="Manage")
        self._prof_btn.add_css_class("flat")
        self._prof_btn.add_css_class("nm-profile-chip")
        self._prof_btn.connect("clicked", self._on_profiles_clicked)
        profile_box.append(self._prof_btn)
        sidebar_box.append(profile_box)

        sep = Gtk.Separator()
        sep.set_margin_top(6)
        sidebar_box.append(sep)

        # Sidebar list
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_vexpand(True)

        self._listbox = Gtk.ListBox()
        self._listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self._listbox.add_css_class("navigation-sidebar")
        self._listbox.connect("row-selected", self._on_row_selected)

        for page_id, icon, label in SIDEBAR_PAGES:
            row = self._make_sidebar_row(page_id, icon, label)
            self._listbox.append(row)
            self._sidebar_rows[page_id] = row

        scroll.set_child(self._listbox)
        sidebar_box.append(scroll)

        nav.set_child(sidebar_box)
        return nav

    def _make_sidebar_row(self, page_id: str, icon: str, label: str) -> Gtk.ListBoxRow:
        row = Gtk.ListBoxRow()
        row.page_id = page_id  # type: ignore[attr-defined]

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        box.set_margin_start(6)
        box.set_margin_end(6)
        box.set_margin_top(4)
        box.set_margin_bottom(4)

        icon_img = Gtk.Image(icon_name=icon)
        icon_img.add_css_class("nm-sidebar-icon")
        box.append(icon_img)

        text_lbl = Gtk.Label(label=label, xalign=0)
        text_lbl.set_hexpand(True)
        box.append(text_lbl)

        badge = Gtk.Label(label="")
        badge.add_css_class("nm-badge")
        badge.set_visible(False)
        box.append(badge)
        self._badge_labels[page_id] = badge

        row.set_child(box)
        return row

    def _build_content_nav(self) -> Adw.NavigationPage:
        self._content_nav = Adw.NavigationPage(title="")

        content_root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        self._stack = Gtk.Stack()
        self._stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self._stack.set_transition_duration(120)
        self._stack.set_vexpand(True)
        content_root.append(self._stack)

        # Build all pages lazily (add placeholders now, build on first visit)
        self._build_all_pages()
        self._build_search_index()

        self._dirty_bar = self._build_dirty_bar()
        content_root.append(self._dirty_bar)

        self._content_nav.set_child(content_root)
        return self._content_nav

    def _build_dirty_bar(self) -> Gtk.Box:
        bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        bar.add_css_class("nm-dirty-bar")
        bar.set_visible(False)
        bar.set_margin_start(12)
        bar.set_margin_end(12)
        bar.set_margin_top(6)
        bar.set_margin_bottom(6)

        lbl = Gtk.Label(label="Unsaved changes")
        lbl.set_hexpand(True)
        lbl.set_xalign(0.0)
        lbl.set_opacity(0.7)
        bar.append(lbl)

        self._undo_btn = Gtk.Button(label="Undo")
        self._undo_btn.add_css_class("flat")
        self._undo_btn.connect("clicked", lambda *_: self._do_undo())
        bar.append(self._undo_btn)

        discard_btn = Gtk.Button(label="Discard")
        discard_btn.add_css_class("destructive-action")
        discard_btn.add_css_class("flat")
        discard_btn.connect("clicked", lambda *_: self._on_discard())
        bar.append(discard_btn)

        save_btn = Gtk.Button(label="Save & Apply")
        save_btn.add_css_class("suggested-action")
        save_btn.connect("clicked", lambda *_: self._on_save())
        bar.append(save_btn)

        return bar

    def _build_all_pages(self):
        """Import and add all page widgets to the stack."""
        from nirimod.pages import (
            outputs,
            keyboard,
            mouse,
            layout,
            appearance,
            animations,
            bindings,
            window_rules,
            startup,
            workspaces,
            environment,
            gestures,
            raw_config,
        )

        page_builders = {
            "outputs": outputs.OutputsPage,
            "keyboard": keyboard.KeyboardPage,
            "mouse": mouse.MousePage,
            "layout": layout.LayoutPage,
            "appearance": appearance.AppearancePage,
            "animations": animations.AnimationsPage,
            "bindings": bindings.BindingsPage,
            "window_rules": window_rules.WindowRulesPage,
            "startup": startup.StartupPage,
            "workspaces": workspaces.WorkspacesPage,
            "environment": environment.EnvironmentPage,
            "gestures": gestures.GesturesPage,
            "raw_config": raw_config.RawConfigPage,
        }
        for page_id, _, title in SIDEBAR_PAGES:
            cls = page_builders.get(page_id)
            if cls:
                page_obj = cls(window=self)
                widget = page_obj.build()
                self._pages[page_id] = page_obj
                self._stack.add_named(widget, page_id)

    def _on_row_selected(self, _lb, row):
        if row is None:
            return
        pid = getattr(row, "page_id", None)
        if pid:
            self._select_page(pid)

    def _select_page(self, page_id: str):
        self._current_page_id = page_id
        self._stack.set_visible_child_name(page_id)
        for pid, _, title in SIDEBAR_PAGES:
            if pid == page_id:
                self._content_nav.set_title(title)
                break
        # select sidebar row
        row = self._sidebar_rows.get(page_id)
        if row:
            self._listbox.select_row(row)

        # Notify page of visibility
        page = self._pages.get(page_id)
        if page and hasattr(page, "on_shown"):
            page.on_shown()

    def _build_search_index(self):
        self._search_index: list[dict] = []

        def traverse(widget, pid, p_title):
            if isinstance(widget, Adw.PreferencesRow):
                title = widget.get_title()
                if title:
                    subtitle = (
                        widget.get_subtitle() if hasattr(widget, "get_subtitle") else ""
                    )
                    self._search_index.append(
                        {
                            "page_id": pid,
                            "page_title": p_title,
                            "title": title,
                            "subtitle": subtitle,
                            "widget": widget,
                        }
                    )

            child = widget.get_first_child()
            while child:
                traverse(child, pid, p_title)
                child = child.get_next_sibling()

        for pid, _icon, p_title in SIDEBAR_PAGES:
            stack_child = self._stack.get_child_by_name(pid)
            if stack_child:
                traverse(stack_child, pid, p_title)

    def _on_search_changed(self, entry):
        query = entry.get_text().strip().lower()
        if not query or len(query) < 2:
            self._search_popover.popdown()
            return

        # Show matching settings in popover
        matches = []
        for r in self._search_index:
            if (
                query in r["title"].lower()
                or query in r["subtitle"].lower()
                or query in r["page_title"].lower()
            ):
                matches.append(r)

        # Clear existing popover rows
        child = self._search_results_listbox.get_first_child()
        while child:
            self._search_results_listbox.remove(child)
            child = self._search_results_listbox.get_first_child()

        if matches:
            for m in matches:
                row = Gtk.ListBoxRow()
                row.search_match = m  # store reference
                box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
                box.set_margin_start(10)
                box.set_margin_end(10)
                box.set_margin_top(8)
                box.set_margin_bottom(8)

                title_lbl = Gtk.Label(label=m["title"], xalign=0)
                title_lbl.add_css_class("heading")
                box.append(title_lbl)

                sub_text = f"{m['page_title']}"
                if m["subtitle"]:
                    sub_text += f" • {m['subtitle']}"

                sub_lbl = Gtk.Label(label=sub_text, xalign=0)
                sub_lbl.add_css_class("dim-label")
                sub_lbl.set_wrap(True)
                sub_lbl.set_wrap_mode(Pango.WrapMode.WORD_CHAR)
                box.append(sub_lbl)

                row.set_child(box)
                self._search_results_listbox.append(row)

            self._search_popover.popup()
        else:
            self._search_popover.popdown()

    def _on_stop_search(self, entry):
        entry.set_text("")
        self._search_popover.popdown()

    def _on_search_result_activated(self, listbox, row):
        if not hasattr(row, "search_match"):
            return

        m = row.search_match
        self._search_popover.popdown()
        self._search_entry.set_text("")

        # Navigate to the page
        self._select_page(m["page_id"])

        # Highlight the widget
        widget = m["widget"]
        widget.add_css_class("nm-pulse-highlight")

        # Remove the highlight after 1.5 seconds
        def remove_class():
            widget.remove_css_class("nm-pulse-highlight")
            return False

        GLib.timeout_add(1500, remove_class)

    # Shortcuts

    def _setup_shortcuts(self):
        app = self.get_application()
        if not app:
            return
        shortcuts = [
            ("save", self._on_save, ["<Control>s"]),
            ("undo", self._do_undo, ["<Control>z"]),
            ("redo", self._do_redo, ["<Control><Shift>z"]),
            ("search", lambda: self._search_entry.grab_focus(), ["<Control>f"]),
        ]
        for name, fn, accels in shortcuts:
            a = Gio.SimpleAction.new(name, None)
            a.connect("activate", lambda _a, _p, f=fn: f())
            self.add_action(a)
            app.set_accels_for_action(f"win.{name}", accels)

    def get_nodes(self):
        return self.app_state.nodes

    def mark_dirty(self):
        """Called by pages when they modify the config."""
        self.app_state.mark_dirty()
        self._dirty_bar.set_visible(True)
        self._undo_btn.set_sensitive(self.app_state.undo.can_undo())

    def mark_clean(self):
        self.app_state.mark_clean()
        self._dirty_bar.set_visible(False)

    def push_undo(self, description: str, before: str, after: str):
        self.app_state.push_undo(description, before, after)
        self._undo_btn.set_sensitive(True)

    def notify_nodes_changed(self):
        """Reload nodes from disk and refresh current page."""
        self.app_state.reload_from_disk()
        page = self._pages.get(self._current_page_id)
        if page and hasattr(page, "refresh"):
            page.refresh()
            self._build_search_index()

    def _on_save(self):
        new_kdl = self.app_state.write_current_kdl()

        tmp_kdl = NIRI_CONFIG.with_name(".config.kdl.tmp")
        self.app_state.write_to_path(tmp_kdl)

        def _on_validated(result):
            ok, msg = result
            if not ok:
                self.show_toast(f"Validation error: {msg}", timeout=8)
                tmp_kdl.unlink(missing_ok=True)
                # Revert UI state cleanly
                self.app_state.discard()
                self.mark_clean()
                self.notify_nodes_changed()
                return

            # Move tmp to main config
            import shutil

            shutil.move(tmp_kdl, NIRI_CONFIG)

            self.app_state.commit_save(new_kdl)
            # Refresh raw config page first, then mark clean to avoid
            # any refresh inadvertently re-showing the dirty bar
            raw = self._pages.get("raw_config")
            if raw and hasattr(raw, "refresh"):
                raw.refresh()
                self._build_search_index()
            self.mark_clean()
            self.show_toast("Config saved and applied ✓", timeout=3)

        niri_ipc.run_in_thread(
            lambda: niri_ipc.validate_config(str(tmp_kdl)), _on_validated
        )

    def _on_discard(self):
        self.app_state.discard()
        self.mark_clean()
        self.notify_nodes_changed()

    def _do_undo(self):
        entry = self.app_state.apply_undo()
        if entry is None:
            return

        if not self.app_state.undo.can_undo():
            self._undo_btn.set_sensitive(False)

        if self.app_state.is_dirty:
            self.mark_dirty()
        else:
            self.mark_clean()

        self.notify_nodes_changed()

    def _do_redo(self):
        entry = self.app_state.apply_redo()
        if entry is None:
            return

        self.mark_dirty()
        self.notify_nodes_changed()

    def show_toast(self, message: str, timeout: int = 3):
        toast = Adw.Toast(title=message, timeout=timeout)
        self._toast_overlay.add_toast(toast)

    def _check_onboarding(self):
        backup_kdl = NIRI_CONFIG.with_suffix(".kdl.bak")
        if backup_kdl.exists():
            return

        # Show dialog
        dialog = Adw.AlertDialog(
            heading="Welcome to NiriMod",
            body=(
                "NiriMod directly edits your main <b>config.kdl</b> file.\n\n"
                "Before proceeding, you should back up your current configuration to\n"
                "<tt>~/.config/niri/config.kdl.bak</tt>.\n"
            ),
        )
        dialog.set_body_use_markup(True)
        dialog.add_response("cancel", "Not Now")
        dialog.add_response("accept", "Create Backup")
        dialog.set_response_appearance("accept", Adw.ResponseAppearance.SUGGESTED)
        dialog.set_default_response("accept")
        dialog.connect("response", self._on_onboarding_response)
        dialog.present(self)

    def _on_onboarding_response(self, dialog, response):
        if response == "accept":
            try:
                if NIRI_CONFIG.exists():
                    import shutil

                    shutil.copy2(NIRI_CONFIG, NIRI_CONFIG.with_suffix(".kdl.bak"))
                    self.show_toast("Backup created successfully ✓")
                else:
                    self.show_toast("config.kdl not found, skipping backup", timeout=6)
            except Exception as e:
                self.show_toast(f"Failed: {e}", timeout=6)

    def _on_profiles_clicked(self, _btn):
        dialog = Adw.AlertDialog(heading="Profiles")

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.set_margin_start(4)
        box.set_margin_end(4)

        names = prof_mod.list_profiles()
        if names:
            grp = Adw.PreferencesGroup(title="Saved Profiles")
            for name in names:
                row = Adw.ActionRow(title=name)
                load_btn = Gtk.Button(label="Load")
                load_btn.set_valign(Gtk.Align.CENTER)
                load_btn.add_css_class("flat")
                load_btn.connect(
                    "clicked", lambda _b, n=name: self._load_profile(n, dialog)
                )
                del_btn = Gtk.Button(icon_name="user-trash-symbolic")
                del_btn.set_valign(Gtk.Align.CENTER)
                del_btn.add_css_class("flat")
                del_btn.add_css_class("error")
                del_btn.connect(
                    "clicked", lambda _b, n=name: self._delete_profile(n, dialog)
                )
                row.add_suffix(load_btn)
                row.add_suffix(del_btn)
                grp.add(row)
            box.append(grp)

        save_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        save_row.set_margin_top(8)
        entry = Gtk.Entry(placeholder_text="New profile name…")
        entry.set_hexpand(True)
        save_btn = Gtk.Button(label="Save Current")
        save_btn.add_css_class("suggested-action")
        save_btn.connect(
            "clicked", lambda _b: self._save_profile(entry.get_text(), dialog)
        )
        save_row.append(entry)
        save_row.append(save_btn)
        box.append(save_row)

        dialog.set_extra_child(box)
        dialog.add_response("close", "Close")
        dialog.present(self)

    def _save_profile(self, name: str, dialog):
        name = name.strip()
        if not name:
            return
        prof_mod.save_profile(name)
        self.show_toast(f"Profile '{name}' saved ✓")

    def _load_profile(self, name: str, dialog):
        if prof_mod.load_profile(name):
            self.notify_nodes_changed()
            self.mark_dirty()
            self.show_toast(f"Profile '{name}' loaded")
        dialog.close()

    def _delete_profile(self, name: str, dialog):
        prof_mod.delete_profile(name)
        self.show_toast(f"Profile '{name}' deleted")
        dialog.close()

    def set_badge(self, page_id: str, count: int):
        lbl = self._badge_labels.get(page_id)
        if lbl:
            if count > 0:
                lbl.set_label(str(count))
                lbl.set_visible(True)
            else:
                lbl.set_visible(False)
