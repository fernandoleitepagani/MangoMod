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

## Features

### Outputs

Live display configuration pulled straight from niri via IPC. Every connected monitor shows up with its real name, current resolution, refresh rate, and scale. You can:

- Pick resolution and refresh rate from the actual mode list niri reports
- Set fractional scale (0.25× to 4.0×)
- Apply output transforms (90°, 180°, 270°, flipped variants)
- Set position with X/Y spinners or by **drag-and-dropping monitors** on the canvas
- Toggle Variable Refresh Rate (VRR) per output
- Disable an output entirely

The canvas keeps a stable scale while dragging and snaps to monitor edges for clean tiling. Positions are written back to config as integers, but fractional pixel boundaries from scaling are handled correctly to avoid niri rejecting the layout.

---

### Keybinds

![Keybinding Management](media/2.png)

Two views in one page:

**Physical keyboard map** — a Cairo-rendered keyboard that lights up bound keys in purple. Modifier keys show a small label when they're part of a binding. Keys with more than one binding get a badge with the count. Click any key to open a panel where you can edit or add bindings for it.

**List view** — a searchable, filterable table of every binding. Add, edit, and remove entries without hunting through the keyboard. The search box filters across both action names and key combos in real time.

---

### Animations

An animation editor where you actually see the easing curve instead of guessing cubic-bezier values and reloading twenty times. Drag the control points on the curve preview, adjust duration, and see the result immediately. Supports all of niri's animation slots (window open/close, workspace switch, etc.).

---

### Layout

Controls the niri column layout: default column widths, preset proportions, gaps, struts, and border settings. Preset proportions are editable as a list of spinners and written back in the correct `proportion` child-node format.

---

### Window Rules

A full editor for niri's `window-rules` block. Rules can be added, removed, and reordered. Each rule supports all match criteria (app-id, title, workspace, etc.) and all rule actions. Leading comments attached to each rule are preserved across edits — removing a rule doesn't silently drop the comment that was above it.

---

### Input

Mouse, touchpad, and keyboard settings in one place — sensitivity, natural scrolling, tap-to-click, accel profiles, key repeat, and XKB options.

---

### Appearance

Cursor theme and size, GTK dark/light preference, and other compositor-level appearance settings.

---

### Gestures

Touchpad gesture configuration: swipe workspace switching, pinch-to-overview, and related options.

---

### Environment

Manage `environment` key-value pairs that niri exports to every launched application. Add and remove entries directly.

---

### Startup

The `spawn-at-startup` list. Add commands that niri runs on startup, remove ones you no longer need.

---

### Workspaces

Named workspace configuration — add, rename, and remove workspaces.

---

### Raw Config Editor

A built-in KDL text editor for when you want to go manual. Has undo/redo, preserved scroll position across saves, and writes back through the same validation pipeline as the GUI controls — so `niri validate` still runs before anything touches disk.

---

## How it stays safe

**Validation before every write.** NiriMod runs `niri validate` on the output before writing anything to disk. If validation fails, nothing is saved and you get the error message.

**Atomic writes.** Config files are written to a temp file in the same directory and then renamed into place — no partial writes, no corruption on interrupted saves.

**Comment and whitespace preservation.** The KDL parser stores each node's leading trivia (comments, blank lines) as part of the parse tree. When NiriMod writes the config back, those comments come with it. You won't lose your `// gaming profile` annotation or the blank lines you use to visually group things.

**Selective editing.** NiriMod only rewrites nodes it manages. Anything it doesn't know about — startup scripts, custom environment vars it hasn't touched, raw nested config — is left exactly as-is.

**Undo/Redo.** `Ctrl+Z` / `Ctrl+Shift+Z`. Up to 100 steps. Works across all pages including the raw editor.

**Profiles.** Save named snapshots of your full config (`~/.config/niri/profiles/`). Works with multi-file configs — the entire file set is snapshotted and restored together. Switch between profiles (e.g. "work", "gaming", "presentation") in one click.

---

## Multi-file configs

![Multi-File Configurations](media/multiple_configs.png)

If you split your niri config with `include` directives, NiriMod handles that. It resolves includes recursively (up to 5 levels), parses all files together into a single flat node list, and tracks which node came from which file. When saving, each node is written back to the file it was loaded from. You don't need to flatten your config.

---

## Install

### AUR (Arch Linux)

NiriMod is available in the AUR as `nirimod-git`.

```bash
yay -S nirimod-git
```

### Script (Other Distros)

```bash
curl -sSL https://raw.githubusercontent.com/srinivasr/nirimod/main/install.sh | bash
```

| Flag | What it does |
| :--- | :--- |
| `--install` | Skip the prompts, install directly |
| `--uninstall` | Remove NiriMod cleanly |
| `--skip-deps` | Skip system package manager checks (for Gentoo, Nix, etc.) |

---

## Requirements

Works on Arch, Fedora, openSUSE, and Debian/Ubuntu out of the box. For Gentoo, use `--skip-deps` and install the packages manually:

**Gentoo** (requires the [GURU overlay](https://wiki.gentoo.org/wiki/Project:GURU) for `niri`):
```bash
emerge dev-vcs/git net-misc/curl dev-lang/python gui-libs/gtk gui-libs/libadwaita dev-python/pygobject dev-python/pycairo x11-libs/libxkbcommon x11-misc/xkeyboard-config
curl -sSL https://raw.githubusercontent.com/srinivasr/nirimod/main/install.sh | bash -s -- --install --skip-deps
```

| Dependency | Notes |
| :--- | :--- |
| Python 3.12+ | Runtime |
| GTK4 + libadwaita | UI toolkit |
| PyGObject & Pycairo | Python ↔ GTK bindings |
| [uv](https://github.com/astral-sh/uv) | Env manager — the installer handles this |
| niri | The compositor you're configuring |

---

## Contributing

Contributions are always welcome! Please check out [CONTRIBUTING.md](CONTRIBUTING.md) for setup instructions and coding standards. If you're planning a major change, please open an issue first to discuss it.

<a href="https://www.star-history.com/?repos=srinivasr%2Fnirimod&type=date&legend=top-left">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/chart?repos=srinivasr/nirimod&type=date&theme=dark&legend=top-left" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/chart?repos=srinivasr/nirimod&type=date&legend=top-left" />
   <img alt="Star History Chart" src="https://api.star-history.com/chart?repos=srinivasr/nirimod&type=date&legend=top-left" />
 </picture>
</a>

---

*NiriMod is an independent project, not affiliated with the niri team.*
