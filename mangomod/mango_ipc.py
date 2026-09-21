"""MangoWM IPC — CLI wrappers."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Callable


def _run(args: list[str], timeout: float = 5.0) -> tuple[str, str, int]:
    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
        return r.stdout, r.stderr, r.returncode
    except FileNotFoundError:
        return "", f"{args[0]}: command not found", 1
    except subprocess.TimeoutExpired:
        return "", f"{args[0]}: timed out", 1


def is_running() -> bool:
    stdout, _, rc = _run(["mango", "msg", "version"])
    return rc == 0 and bool(stdout.strip())


def validate_config(path: str | None = None) -> tuple[bool, str]:
    """Local syntax check + best-effort `mango -c <path> -p`."""
    if not path:
        return True, "No path provided."
    p = Path(path)
    if not p.exists():
        return False, f"File not found: {path}"
    try:
        text = p.read_text()
    except OSError as e:
        return False, f"Read error: {e}"
    for i, line in enumerate(text.splitlines(), 1):
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        if "=" not in s:
            return False, f"Line {i}: missing '=' in '{s}'"
    stdout, stderr, rc = _run(["mango", "-c", str(path), "-p"], timeout=5.0)
    if rc == 0:
        return True, "Config is valid."
    if "not found" in stderr:
        return True, "Basic syntax check passed (mango binary not found)."
    return False, stderr.strip() or stdout.strip() or "Validation failed."


def reload() -> tuple[bool, str]:
    stdout, stderr, rc = _run(["mango", "msg", "reload"], timeout=5.0)
    if rc == 0:
        return True, stdout.strip() or "Config applied."
    return False, stderr.strip() or stdout.strip() or "Reload failed."


def run_in_thread(fn: Callable, callback: Callable | None = None):
    import threading
    import gi
    gi.require_version("GLib", "2.0")
    from gi.repository import GLib

    def _worker():
        result = fn()
        if callback is not None:
            GLib.idle_add(lambda: (callback(result), False)[1])

    t = threading.Thread(target=_worker, daemon=True)
    t.start()
    return t
