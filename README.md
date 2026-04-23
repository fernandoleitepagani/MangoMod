<div align="center">
  <h1>NiriMod</h1>
  
  **A GTK4/libadwaita config manager for the [niri](https://github.com/niri-wm/niri) Wayland compositor.**

  [![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
  [![Python 3.12+](https://img.shields.io/badge/Python-3.12%2B-blue?logo=python&logoColor=white)](https://python.org)
  [![GTK4](https://img.shields.io/badge/GTK-4%20%2B%20libadwaita-4A90D9?logo=gnome&logoColor=white)](https://gtk.org)
  [![Wayland](https://img.shields.io/badge/Wayland-native-orange)](https://wayland.freedesktop.org)
</div>

<br>

![NiriMod Interface](media/1.png)

Niri's config is a KDL file, and editing it by hand works fine — until it doesn't. Tweaking animation curves blind, guessing monitor names, or accidentally overlapping keybinds gets old fast. NiriMod gives you a proper GUI for the stuff that's annoying to do in a text editor, while staying out of the way for everything else.

---

## What it looks like

### Outputs & Animations

The left side handles display config — scaling, resolution, the usual. The right side is an animation editor where you can actually see the easing curve instead of guessing cubic-bezier values and reloading twenty times.

*(That's the screenshot above.)*

---

### Keybinds

![Keybinding Management](media/2.png)

Two views: a physical keyboard map that shows you which keys are bound (so you stop clobbering your own shortcuts), and a searchable list for when you just want to find and change something quickly.

---

### Multi-file configs

![Multi-File Configurations](media/multiple_configs.png)

If you split your niri config across multiple files with `include` directives, NiriMod handles that. It parses all the included files together and writes changes back to the correct file. You don't need to flatten your config to use this.

---

## Demo

https://github.com/user-attachments/assets/demo.mp4

> *If the video doesn't load, grab [`demo.mp4`](media/demo.mp4) directly.*

---

## How it stays safe

NiriMod won't write a broken config to disk. Every save runs through `niri validate` first — if it doesn't pass, nothing gets written.

Beyond that:

- **Undo/Redo** — `Ctrl+Z` / `Ctrl+Shift+Z`, unlimited history
- **Config preservation** — NiriMod only touches settings it manages. Your startup commands, scripts, and anything it doesn't understand are left alone.
- **Profiles** — save named config snapshots ("deep work", "gaming", etc.) and switch between them
- **Raw mode** — built-in KDL editor with syntax highlighting for when you want to go manual

---

## Install

```bash
curl -sSL https://raw.githubusercontent.com/srinivasr/nirimod/main/install.sh | bash
```

This runs an interactive installer that handles dependencies for you.

| Flag | What it does |
| :--- | :--- |
| `--install` | Skip the prompts, install directly |
| `--uninstall` | Remove NiriMod cleanly |

---

## Requirements

Works on Arch, Fedora, openSUSE, and Debian/Ubuntu.

| Dependency | Notes |
| :--- | :--- |
| Python 3.12+ | Runtime |
| GTK4 + libadwaita | UI toolkit |
| PyGObject | Python ↔ GTK bindings |
| [uv](https://github.com/astral-sh/uv) | Env manager — the installer handles this |
| niri | The compositor you're configuring |

---

Inspired by [Hyprmod](https://github.com/BlueManCZ/hyprmod).

*NiriMod is an independent project, not affiliated with the niri team.*
