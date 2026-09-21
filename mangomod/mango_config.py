"""Flat key=value config parser/writer for MangoWM, with source= support.

Comments and blank lines are preserved verbatim across saves. Only lines
that parse as `key=value` are treated as editable entries.
"""

from __future__ import annotations

import os
import stat
import tempfile
from dataclasses import dataclass
from pathlib import Path

_config_dir = Path(
    os.environ.get("MANGOMOD_CONFIG_DIR", Path.home() / ".config" / "mango")
)
MANGO_CONFIG = _config_dir / "config.conf"

_SOURCE_KEYS = ("source", "source-optional")
_MAX_DEPTH = 8


def set_paths(config_path: str | Path | None = None) -> None:
    global MANGO_CONFIG, _config_dir
    if config_path:
        p = Path(config_path).expanduser().resolve()
        _config_dir = p.parent
        MANGO_CONFIG = p
    else:
        _config_dir = Path(
            os.environ.get("MANGOMOD_CONFIG_DIR", Path.home() / ".config" / "mango")
        )
        MANGO_CONFIG = _config_dir / "config.conf"


@dataclass
class Line:
    """One line of a config file.

    kind == "entry": an editable `key=value` line.
    kind == "raw":   a comment, blank line, or unparsable line kept verbatim.
    """

    kind: str
    source: Path
    key: str = ""
    value: str = ""
    raw: str = ""

    def is_entry(self) -> bool:
        return self.kind == "entry"

    def to_text(self) -> str:
        if self.kind == "entry":
            return f"{self.key}={self.value}"
        return self.raw


class MangoConfig:
    def __init__(self, main_path: Path | None = None):
        self.main_path: Path = main_path or MANGO_CONFIG
        # Per-file ordered list of Line objects. Preserves comments,
        # blank lines, and original line ordering.
        self._lines_by_file: dict[Path, list[Line]] = {}
        self.source_files: list[Path] = []
        self._seen: set[Path] = set()

    # ── loading ─────────────────────────────────────────────────────

    def load(self) -> None:
        self._lines_by_file.clear()
        self.source_files.clear()
        self._seen = {self.main_path}
        self._load_file(self.main_path, depth=0)

    def _load_file(self, path: Path, depth: int) -> None:
        if depth > _MAX_DEPTH:
            return
        lines = self._lines_by_file.setdefault(path, [])
        if not path.exists():
            return
        try:
            text = path.read_text().replace("\r\n", "\n")
        except OSError:
            return

        for raw_line in text.split("\n"):
            stripped = raw_line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                lines.append(Line(kind="raw", source=path, raw=raw_line))
                continue

            key, _, value = stripped.partition("=")
            key, value = key.strip(), value.strip()
            lines.append(Line(kind="entry", source=path, key=key, value=value))

            if key in _SOURCE_KEYS:
                target = self._resolve_path(path, value)
                if target is None or target == self.main_path or target in self._seen:
                    continue
                self._seen.add(target)
                self.source_files.append(target)
                self._load_file(target, depth + 1)

    @staticmethod
    def _resolve_path(base_file: Path, raw: str) -> Path | None:
        raw = raw.strip().strip('"').strip("'")
        if not raw:
            return None
        p = Path(os.path.expanduser(raw))
        if not p.is_absolute():
            p = (base_file.parent / p).resolve()
        return p

    # ── internal iteration ──────────────────────────────────────────

    def _all_lines(self):
        yield from self._lines_by_file.get(self.main_path, [])
        for path in self.source_files:
            yield from self._lines_by_file.get(path, [])

    def _entry_lines(self):
        for ln in self._all_lines():
            if ln.is_entry():
                yield ln

    # ── queries ─────────────────────────────────────────────────────

    def get(self, key: str, default: str | None = None) -> str | None:
        for ln in self._all_lines():
            if ln.is_entry() and ln.key == key:
                return ln.value
        return default

    def get_all(self, key: str) -> list[str]:
        return [ln.value for ln in self._all_lines()
                if ln.is_entry() and ln.key == key]

    def get_all_keyed(self) -> list[tuple[str, str]]:
        return [(ln.key, ln.value) for ln in self._entry_lines()]

    def entries_with_source(self, key: str) -> list[tuple[str, str, Path]]:
        """All matching (key, value, source) triples, in load order."""
        return [(ln.key, ln.value, ln.source) for ln in self._all_lines()
                if ln.is_entry() and ln.key == key]

    def has(self, key: str) -> bool:
        return any(ln.is_entry() and ln.key == key for ln in self._all_lines())

    def all_files(self) -> list[Path]:
        return [self.main_path, *self.source_files]

    # ── mutations ───────────────────────────────────────────────────

    def set(self, key: str, value) -> None:
        """Update in place if the key exists; else append to the main file."""
        value = _stringify(value)
        for ln in self._all_lines():
            if ln.is_entry() and ln.key == key:
                ln.value = value
                return
        self._append_entry(self.main_path, key, value)

    def add(self, key: str, value, source: Path | None = None) -> None:
        self._append_entry(source or self.main_path, key, _stringify(value))

    def _append_entry(self, path: Path, key: str, value: str) -> None:
        lines = self._lines_by_file.setdefault(path, [])
        new_line = Line(kind="entry", source=path, key=key, value=value)
        # If the file ends with the trailing "" from a final newline,
        # insert the new entry before it so we don't leave a blank line.
        if lines and lines[-1].kind == "raw" and lines[-1].raw == "":
            lines.insert(len(lines) - 1, new_line)
        else:
            lines.append(new_line)

    def remove(self, key: str) -> None:
        for path in list(self._lines_by_file.keys()):
            self._lines_by_file[path] = [
                ln for ln in self._lines_by_file[path]
                if not (ln.is_entry() and ln.key == key)
            ]

    def remove_value(self, key: str, value: str) -> None:
        for path in list(self._lines_by_file.keys()):
            self._lines_by_file[path] = [
                ln for ln in self._lines_by_file[path]
                if not (ln.is_entry() and ln.key == key and ln.value == value)
            ]

    def remove_nth(self, key: str, ordinal: int) -> None:
        count = 0
        for path in list(self._lines_by_file.keys()):
            new_lines: list[Line] = []
            for ln in self._lines_by_file[path]:
                if ln.is_entry() and ln.key == key:
                    if count == ordinal:
                        count += 1
                        continue
                    count += 1
                new_lines.append(ln)
            self._lines_by_file[path] = new_lines

    def replace_nth(
        self, key: str, ordinal: int, new_value, new_key: str | None = None
    ) -> None:
        count = 0
        nv = _stringify(new_value)
        for ln in self._all_lines():
            if ln.is_entry() and ln.key == key:
                if count == ordinal:
                    if new_key is not None:
                        ln.key = new_key
                    ln.value = nv
                    return
                count += 1

    # ── serialization ───────────────────────────────────────────────

    def write_file(self, path: Path) -> str:
        lines = self._lines_by_file.get(path, [])
        if not lines:
            return ""
        text = "\n".join(ln.to_text() for ln in lines)
        if not text.endswith("\n"):
            text += "\n"
        return text

    def write(self) -> str:
        return self.write_file(self.main_path)

    def write_all(self) -> None:
        for path in self.all_files():
            text = self.write_file(path)
            if text or path.exists():
                _atomic_write(path, text)


# ── shared rule helpers ─────────────────────────────────────────────

def parse_kv_rule(rule: str) -> dict[str, str]:
    """Parse a comma-separated key:value rule (monitorrule / windowrule / layerrule)."""
    out: dict[str, str] = {}
    for part in rule.split(","):
        if ":" in part:
            k, _, v = part.partition(":")
            out[k.strip()] = v.strip()
    return out


def build_kv_rule(parts: dict[str, str]) -> str:
    """Serialize a dict back to a comma-separated key:value rule."""
    return ",".join(f"{k}:{v}" for k, v in parts.items())


# ── internals ───────────────────────────────────────────────────────

def _stringify(value) -> str:
    if value is True:
        return "1"
    if value is False:
        return "0"
    return str(value)


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        mode = stat.S_IMODE(path.stat().st_mode)
    except FileNotFoundError:
        mode = None
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".mangomod_tmp_")
    ok = False
    try:
        os.write(fd, content.encode())
        if mode is not None:
            os.fchmod(fd, mode)
        os.close(fd)
        fd = -1
        os.replace(tmp, path)
        ok = True
    finally:
        if fd != -1:
            os.close(fd)
        if not ok:
            try:
                os.unlink(tmp)
            except OSError:
                pass


def load_config(path: Path | None = None) -> MangoConfig:
    cfg = MangoConfig(path or MANGO_CONFIG)
    cfg.load()
    return cfg


def save_config(config: MangoConfig, path: Path | None = None) -> None:
    if path is not None:
        _atomic_write(path, config.write())
    else:
        config.write_all()
