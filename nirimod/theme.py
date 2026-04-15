"""CSS theme definitions for NiriMod."""

CSS = b"""
/* NiriMod Premium Aesthetics - Deep Charcoal Overrides */

@define-color nm_accent #3584e4;

/* Override standard Libadwaita colors */
@define-color window_bg_color #0d0d0d;
@define-color window_fg_color #eeeeee;
@define-color view_bg_color #141414;
@define-color view_fg_color #eeeeee;
@define-color headerbar_bg_color #0d0d0d;
@define-color card_bg_color #181818;
@define-color card_fg_color #eeeeee;
@define-color popover_bg_color #1c1c1c;
@define-color popover_fg_color #eeeeee;
@define-color dialog_bg_color #111111;
@define-color dialog_fg_color #eeeeee;

@define-color nm_border rgba(255, 255, 255, 0.06);

window {
    background-color: @window_bg_color;
    color: @window_fg_color;
}

headerbar,
.nm-sidebar-bg {
    background-color: @window_bg_color;
    background-image: none;
    box-shadow: none;
    border-bottom: 1px solid @nm_border;
}

.navigation-sidebar {
    background-color: @window_bg_color;
    border-right: 1px solid @nm_border;
}

.nm-sidebar-row {
    padding: 10px 14px;
    margin: 2px 8px;
    border-radius: 10px;
    transition: all 200ms ease;
    font-weight: 500;
}

.nm-sidebar-row:hover {
    background: alpha(white, 0.04);
}

.nm-sidebar-row:selected,
.nm-sidebar-row.selected {
    background: alpha(@nm_accent, 0.12);
    color: @nm_accent;
}

.nm-card,
preferencesgroup > box {
    background-color: @card_bg_color;
    border: 1px solid @nm_border;
    border-radius: 16px;
    padding: 4px;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.3);
}

row {
    border-radius: 12px;
    transition: background 150ms ease;
}

row:hover {
    background: alpha(white, 0.03);
}

.nm-badge {
    background: @nm_accent;
    color: white;
    border-radius: 20px;
    font-size: 11px;
    font-weight: 800;
    padding: 1px 8px;
    min-width: 16px;
}

.nm-dirty-bar {
    background: alpha(@nm_accent, 0.1);
    border-top: 1px solid alpha(@nm_accent, 0.2);
    padding: 12px 24px;
}

.nm-page-title {
    font-size: 26px;
    font-weight: 800;
    letter-spacing: -0.8px;
}

.nm-search-entry {
    background: alpha(white, 0.05);
    border: 1px solid @nm_border;
    border-radius: 12px;
}

button.suggested-action {
    border-radius: 10px;
    font-weight: 600;
}

@keyframes pulse-highlight {
    0% { background-color: alpha(white, 0.0); }
    15% { background-color: alpha(@nm_accent, 0.4); box-shadow: 0 0 12px alpha(@nm_accent, 0.6); }
    100% { background-color: alpha(white, 0.0); box-shadow: none; }
}

.nm-pulse-highlight {
    animation-name: pulse-highlight;
    animation-duration: 1.5s;
    animation-timing-function: ease-out;
}

/* -- Keyboard Visualizer --------------------------------------------------- */

.nm-kb-action-panel {
    background-color: @card_bg_color;
    border: 1px solid @nm_border;
    border-radius: 16px;
    padding: 4px;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.3);
}

.nm-kb-key-id-label {
    font-size: 22px;
    font-weight: 800;
    letter-spacing: -0.5px;
    color: @window_fg_color;
}

.nm-kb-swatch {
    min-width: 12px;
    min-height: 12px;
    border-radius: 3px;
}

/* -- Keycaps for Bindings List ------------------------------------------- */

.nm-keycap-main, .nm-keycap-mod {
    background-color: alpha(@window_fg_color, 0.08); /* slight translucent */
    border: 1px solid alpha(@window_fg_color, 0.15); /* solid subtle border */
    border-radius: 6px; /* slightly sharp for keys */
    padding: 2px 8px; /* good breathability */
    font-size: 13px;
    font-weight: 700; /* bold text */
    color: @window_fg_color;
    box-shadow: 0 2px 0 alpha(@window_fg_color, 0.1); /* bottom key depth */
}

.nm-keycap-main {
    background-color: alpha(@accent_color, 0.15);
    border-color: alpha(@accent_color, 0.4);
    color: @accent_color;
    font-size: 14px;
    font-weight: 800; /* Extra bold for main key */
}

.nm-keycap-mod {
    opacity: 0.8; /* modifiers slightly recede */
}
"""
