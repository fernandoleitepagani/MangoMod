"""CSS theme definitions for MangoMod."""

CSS = """
/* --- MangoMod -- Adwaita Blue Theme --- */

/* --- Accent (GNOME Adwaita Blue) --- */
@define-color nm_accent         #3584e4;
@define-color nm_accent_mid     #1c71d8;
@define-color nm_accent_dim     rgba(53, 132, 228, 0.13);
@define-color nm_accent_hover   rgba(53, 132, 228, 0.20);
@define-color nm_accent_border  rgba(53, 132, 228, 0.28);

/* --- Surfaces --- */
@define-color window_bg_color    #111114;
@define-color window_fg_color    #e8e8ed;
@define-color view_bg_color      #18181c;
@define-color view_fg_color      #e8e8ed;
@define-color headerbar_bg_color #111114;
@define-color card_bg_color      #1e1e24;
@define-color card_fg_color      #e8e8ed;
@define-color popover_bg_color   #1e1e24;
@define-color popover_fg_color   #e8e8ed;
@define-color dialog_bg_color    #18181c;
@define-color dialog_fg_color    #e8e8ed;

/* --- Borders --- */
@define-color nm_border         rgba(255, 255, 255, 0.07);
@define-color nm_border_strong  rgba(255, 255, 255, 0.12);

/* --- Window --- */
window {
    background-color: @window_bg_color;
    color: @window_fg_color;
}

/* --- Header Bars --- */
headerbar,
.nm-sidebar-bg {
    background-color: @window_bg_color;
    background-image: none;
    box-shadow: none;
    border-bottom: 1px solid @nm_border;
    color: @window_fg_color;
}

/* --- Sidebar --- */
.navigation-sidebar {
    background-color: transparent;
    border-right: 1px solid @nm_border;
}

.nm-sidebar-listbox {
    background: transparent;
    border: none;
}

.nm-sidebar-listbox row {
    border-radius: 7px;
    margin: 1px 4px;
    padding: 5px 8px;
    transition: background 130ms ease;
    color: @window_fg_color;
}

.nm-sidebar-listbox row:hover {
    background: rgba(255, 255, 255, 0.045);
}

.nm-sidebar-listbox row:selected {
    background: @nm_accent_dim;
    color: @nm_accent;
}

.nm-sidebar-listbox row:selected image,
.nm-sidebar-listbox row:selected label {
    color: @nm_accent;
}

/* --- Section Labels --- */
.nm-sidebar-section-label {
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.08em;
    color: rgba(255, 255, 255, 0.30);
}

/* --- Content Cards --- */
preferencesgroup > box {
    background-color: @card_bg_color;
    border: 1px solid @nm_border;
    border-radius: 12px;
    padding: 4px;
}

row {
    border-radius: 7px;
    transition: background 110ms ease;
}

row:hover {
    background: rgba(255, 255, 255, 0.025);
}

/* --- Unsaved Changes Bar --- */
.nm-dirty-bar {
    background: rgba(53, 132, 228, 0.07);
    border-top: 1px solid rgba(53, 132, 228, 0.18);
    padding: 8px 20px;
}

/* --- Mango Banner --- */
.nm-mango-banner {
    background: rgba(180, 110, 0, 0.10);
    color: rgba(240, 180, 50, 0.90);
    padding: 6px 16px;
    font-size: 13px;
    border-bottom: 1px solid rgba(180, 110, 0, 0.18);
}

/* --- Buttons --- */
button.suggested-action {
    border-radius: 9px;
    font-weight: 600;
    background: @nm_accent_mid;
}

/* --- Toasts --- */
toast {
    background-color: @card_bg_color;
    color: @card_fg_color;
    border: 1px solid @nm_accent_border;
    border-radius: 20px;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.45);
    margin-bottom: 20px;
}

toast label { font-weight: 500; }

/* --- Code Editor --- */
.code-editor {
    background-color: #0d0d10;
    color: #e8e8ed;
    border: 1px solid @nm_border;
    border-radius: 10px;
}
""".encode("utf-8")
