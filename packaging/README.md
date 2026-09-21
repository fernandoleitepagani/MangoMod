# Packaging

Four installers are provided. All of them read `pyproject.toml`
at the repo root — no per-package version duplication.

| Format | Target | Command |
|---|---|---|
| Flatpak | Distro-agnostic | `flatpak-builder --user --install build packaging/flatpak/io.github.mangomod.yml` |
| Arch | `pacman` | `cd packaging/arch && makepkg -si` |
| Fedora | `dnf` / `rpm` | `rpmbuild -ba packaging/fedora/mangomod.spec` |
| Debian | `apt` / `dpkg` | `cd packaging/debian && debuild -us -uc` |

## Runtime dependencies

- Python 3.12+
- PyGObject (`python3-gobject` / `python3-gi` / `python-gobject`)
- GTK 4
- libadwaita
- `wlr-randr` (optional; the Outputs page falls back to `/sys/class/drm`
  and config parsing when it's absent)

## Versioning

The version comes from `pyproject.toml`. When you bump it:
- Arch: update `pkgver` in `PKGBUILD`, reset `pkgrel=1`
- Fedora: update `Version:` in `.spec`, add a `%changelog` entry
- Debian: add a new entry via `dch -v <version>-1`
- Flatpak: point the source `tag:` at the new git tag
