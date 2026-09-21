<div align="center">
  <h1>MangoMod</h1>
  
  **GTK4/libadwaita configuration editor for the [MangoWM](https://github.com/mangowm/mango) Wayland compositor, based on [NiriMod](https://github.com/srinivasr/nirimod).**

  [![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
  [![Python 3.12+](https://img.shields.io/badge/Python-3.12%2B-blue?logo=python&logoColor=white)](https://python.org)
  [![GTK4](https://img.shields.io/badge/GTK-4%20%2B%20libadwaita-4A90D9?logo=gnome&logoColor=white)](https://gtk.org)
  [![Wayland](https://img.shields.io/badge/Wayland-native-orange)](https://wayland.freedesktop.org)
</div>

<br>

Best for work that requires visualizing changes, such as changing display settings and position

## Features

- Drag-and-drop monitor layout arrangement, resolution, refresh rate, variable refresh rate (VRR), and fractional scaling.
- Gaps, borders, and per-tag layout customization.
- Mouse, touchpad, and trackpoint settings 
- Built-in config.conf editor

## Configuration Safety

- Invalid configurations are blocked and surfaced with compiler diagnostics.
- Custom comments, whitespace, and formatting are preserved across round-trips.

### Multi-File and Desktop Shell Setups

Mango configurations frequently use `source` directives to separate concerns across files 

The app resolves `source` paths just fine, working flawlessly to update and verify all `.conf` files.


## Installation

### Installation Script

```bash
curl -sSL https://raw.githubusercontent.com/fernandoleitepagani/MangoMod/main/install.sh | bash
```

Use `--install` for non-interactive installs, `--uninstall` to remove, or `--skip-deps` to bypass package manager checks.

## Dependencies

- Python 3.12+ and `uv`
- GTK4, libadwaita, PyGObject, and Pycairo
- `mango` compositor binary


## Future

still has many features to implement and polish:

- [ ] Update keybindings section so it detects ALL keybindings (for example, rofi keybindings)
- [ ] Port it to C
- [ ] Add ability to detect current window manager and let user use it regardless of the WM (hyprland, niri, mango)

## Contributing

Review [CONTRIBUTING.md](CONTRIBUTING.md) for local development setup and style expectations. Feel free to open issues and make new PRs.

*MangoMod is an independent project and is not affiliated with the official mango team or the original developer of NiriMod.*
