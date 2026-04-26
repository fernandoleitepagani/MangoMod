"""CSS theme definitions for NiriMod."""

CSS = b"""
/* NiriMod -- Clean Grouped Sidebar Theme */

@define-color nm_accent #9333ea;
@define-color nm_accent_dim rgba(147, 51, 234, 0.15);

/* Base Adwaita overrides */
@define-color window_bg_color #0d0d0f;
@define-color window_fg_color #e8e8ec;
@define-color view_bg_color #13131a;
@define-color view_fg_color #e8e8ec;
@define-color headerbar_bg_color #0d0d0f;
@define-color card_bg_color #1a1a22;
@define-color card_fg_color #e8e8ec;
@define-color popover_bg_color #1e1e28;
@define-color popover_fg_color #e8e8ec;
@define-color dialog_bg_color #141420;
@define-color dialog_fg_color #e8e8ec;

@define-color nm_border rgba(255, 255, 255, 0.06);
@define-color nm_border_hover rgba(147, 51, 234, 0.3);

window {
    background-color: @window_bg_color;
    color: @window_fg_color;
}

/* --- Sidebar --- */

headerbar,
.nm-sidebar-bg {
    background-color: @window_bg_color;
    background-image: none;
    box-shadow: none;
    border-bottom: 1px solid @nm_border;
    color: @window_fg_color;
}

.navigation-sidebar {
    background-color: transparent;
    border-right: 1px solid @nm_border;
}

.nm-sidebar-listbox {
    background: transparent;
    border: none;
    border-radius: 10px;
}

.nm-sidebar-listbox row {
    border-radius: 8px;
    margin: 1px 0;
    padding: 6px 10px;
    transition: background 150ms ease;
    color: @window_fg_color;
}

.nm-sidebar-listbox row:hover {
    background: rgba(255, 255, 255, 0.05);
}

.nm-sidebar-listbox row:selected {
    background: @nm_accent_dim;
    color: @nm_accent;
}

.nm-sidebar-listbox row:selected image,
.nm-sidebar-listbox row:selected label {
    color: @nm_accent;
}

/* Section headers in sidebar */
.nm-sidebar-section-label {
    font-size: 10px;
    font-weight: 800;
    letter-spacing: 0.1em;
    color: rgba(255, 255, 255, 0.3);
}

/* Search results popover */
.nm-search-results {
    background: transparent;
    border: none;
}

.nm-search-results row {
    padding: 8px 12px;
    border-radius: 8px;
    margin: 2px 4px;
    transition: background 120ms ease;
}

.nm-search-results row:hover {
    background: rgba(147, 51, 234, 0.12);
}

/* --- Content Cards --- */

.nm-card,
preferencesgroup > box {
    background-color: @card_bg_color;
    border: 1px solid @nm_border;
    border-radius: 14px;
    padding: 4px;
}

row {
    border-radius: 10px;
    transition: background 150ms ease;
}

row:hover {
    background: rgba(255, 255, 255, 0.03);
}

/* --- Badges & Status --- */

.nm-badge {
    background: @nm_accent;
    color: white;
    border-radius: 20px;
    font-size: 10px;
    font-weight: 800;
    padding: 1px 7px;
    min-width: 16px;
}

.nm-search-entry {
    color: @window_fg_color;
    background-color: @card_bg_color;
    border: 1px solid @nm_border;
    border-radius: 8px;
}

.nm-search-entry > box {
    color: @window_fg_color;
}

.nm-search-entry text {
    color: @window_fg_color;
}

.nm-dirty-bar {
    background: rgba(147, 51, 234, 0.08);
    border-top: 1px solid rgba(147, 51, 234, 0.2);
    padding: 10px 24px;
}

/* Inline tag badges (used in window rules rows) */
.tag {
    background: rgba(255, 255, 255, 0.08);
    color: @window_fg_color;
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 6px;
    font-size: 11px;
    font-weight: 600;
    padding: 1px 7px;
}

.tag.accent {
    background: @nm_accent_dim;
    color: rgba(192, 132, 252, 1.0);
    border-color: rgba(147, 51, 234, 0.3);
}

.nm-niri-banner {
    background: rgba(200, 130, 0, 0.12);
    color: rgba(255, 190, 60, 1.0);
    padding: 6px 16px;
    font-size: 13px;
    border-bottom: 1px solid rgba(200, 130, 0, 0.2);
}

/* --- Typography --- */

.nm-page-title {
    font-size: 24px;
    font-weight: 800;
    letter-spacing: -0.5px;
}

/* --- Buttons --- */

button.suggested-action {
    border-radius: 10px;
    font-weight: 600;
    background: @nm_accent;
}

/* --- Pulse Highlight (search) --- */

@keyframes pulse-highlight {
    0%   { background-color: transparent; }
    15%  { background-color: rgba(147, 51, 234, 0.35); box-shadow: 0 0 12px rgba(147, 51, 234, 0.5); }
    100% { background-color: transparent; box-shadow: none; }
}

.nm-pulse-highlight {
    animation-name: pulse-highlight;
    animation-duration: 1.5s;
    animation-timing-function: ease-out;
}

/* --- Keyboard Visualizer --- */

.nm-kb-action-panel {
    background-color: @card_bg_color;
    border: 1px solid @nm_border;
    border-radius: 14px;
    padding: 4px;
}

.nm-kb-key-id-label {
    font-size: 20px;
    font-weight: 800;
    letter-spacing: -0.5px;
    color: @window_fg_color;
}

.nm-kb-swatch {
    min-width: 12px;
    min-height: 12px;
    border-radius: 3px;
}

/* --- Keycaps --- */

.nm-keycap-main, .nm-keycap-mod {
    background-color: rgba(147, 51, 234, 0.15);
    border: 1px solid rgba(147, 51, 234, 0.35);
    border-radius: 6px;
    padding: 2px 8px;
    font-size: 12px;
    font-weight: 700;
    color: rgba(192, 132, 252, 1.0);
    box-shadow: 0 2px 0 rgba(0, 0, 0, 0.3);
}

.nm-keycap-main {
    background-color: rgba(147, 51, 234, 0.25);
    border-color: rgba(168, 85, 247, 0.6);
    color: rgba(216, 180, 254, 1.0);
    font-weight: 800;
}

.nm-keycap-mod {
    opacity: 0.85;
}

/* Binding list cards */
.nm-keycap-purple {
    background: rgba(88, 28, 135, 0.7);
    color: rgba(216, 180, 254, 1.0);
    border: 1px solid rgba(147, 51, 234, 0.5);
    border-radius: 6px;
    padding: 2px 8px;
    font-weight: bold;
    font-size: 12px;
    box-shadow: 0 2px 0 rgba(0, 0, 0, 0.3);
}
/* --- Toasts --- */

toast {
    background-color: @card_bg_color;
    color: @card_fg_color;
    border: 1px solid @nm_border_hover;
    border-radius: 24px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.5);
    margin-bottom: 24px;
}

toast label {
    font-weight: 500;
}

/* --- Code Editor --- */

.code-editor {
    background-color: #08080b;
    color: #e8e8ec;
    border: 1px solid @nm_border;
    border-radius: 12px;
}

/* --- Animations Page --- */

.nm-anim-banner {
    background: rgba(147, 51, 234, 0.10);
    border: 1px solid rgba(147, 51, 234, 0.25);
    border-radius: 12px;
    padding: 10px 16px;
    color: rgba(192, 132, 252, 1.0);
}

.nm-anim-banner button {
    background: rgba(147, 51, 234, 0.20);
    border: 1px solid rgba(147, 51, 234, 0.35);
    color: rgba(216, 180, 254, 1.0);
    font-weight: 600;
    border-radius: 20px;
    padding: 4px 14px;
}

.nm-anim-banner button:hover {
    background: rgba(147, 51, 234, 0.35);
}

.nm-preset-icon {
    font-size: 18px;
    min-width: 28px;
}
"""

