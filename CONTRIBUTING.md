# Contributing to NiriMod

Thanks for your interest in contributing! NiriMod is a growing project and PRs are welcome.

## Development setup

System dependencies (Debian/Ubuntu names; adapt for your distro):

```bash
libcairo2-dev libgirepository-2.0-dev libgtk-4-dev libadwaita-1-dev
```

Then:

```bash
git clone https://github.com/srinivasr/nirimod.git
cd nirimod
uv sync
uv run nirimod
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

## Code style

- Ruff enforces linting and formatting rules. Always run with `--fix` and `format`.
- Mypy must pass clean. Don't use `assert` for type narrowing — restructure the code instead.
- Follow existing patterns for option rows, pages, and GTK widgets rather than inventing new ones.

## Scope

- For larger changes, open an issue first so we can discuss the approach.
- System settings that aren't managed by Niri (like Wi-Fi, Bluetooth, general theming outside of compositor scopes) are out of scope.

## Reporting bugs

Open a [GitHub issue](https://github.com/srinivasr/nirimod/issues) and include:

- Niri version (`niri --version`)
- Steps to reproduce
- Relevant log output, if any
