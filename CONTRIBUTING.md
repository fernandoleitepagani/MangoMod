# Contributing to NiriMod

## Development setup

System dependencies (Fedora/DNF names; adapt for your distro):

```bash
cairo-devel gobject-introspection-devel gtk4-devel libadwaita-devel
```

Then:

```bash
git clone https://github.com/fernandoleitepagani/MangoMod.git
cd MangoMod 
uv sync
uv run mangomod
```

Requires Python 3.12+ and a running Niri instance for full manual testing.

## Before submitting a PR

Run the same checks that CI runs:

```bash
uv run ruff check --fix .
uv run ruff format .
uv run mypy nirimod
uv run pytest
```

All checks must pass before your PR can be merged.

## Scope

- For larger changes, open an issue first so we can discuss the approach.
- System settings that aren't managed by Mango (like Wi-Fi, Bluetooth, general theming outside of compositor scopes) are out of scope.

## Reporting bugs

Open a [GitHub issue](https://github.com/srinivasr/nirimod/issues) and include:

- Niri version (`niri --version`)
- Steps to reproduce
- Relevant log output, if any
