import json
import os
import subprocess
import tempfile
import urllib.request
import stat
import threading
from gi.repository import GLib

API_URL = "https://api.github.com/repos/srinivasr/nirimod/commits/main"
INSTALL_DIR = os.path.expanduser("~/.local/share/nirimod")


def check_for_updates(callback):
    # Runs in a background thread so the UI stays responsive.
    # Calls callback(sha, message) if there's something new, or callback(None, None) otherwise.
    def _do_check():
        try:
            if not os.path.isdir(os.path.join(INSTALL_DIR, ".git")):
                # not a git install, nothing we can do
                GLib.idle_add(callback, None, None)
                return

            local_hash = subprocess.check_output(
                ["git", "rev-parse", "HEAD"],
                cwd=INSTALL_DIR,
                text=True,
            ).strip()

            req = urllib.request.Request(API_URL, headers={"User-Agent": "NiriMod-Updater"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                remote_hash = data.get("sha")
                commit_msg = data.get("commit", {}).get("message", "New update available")

            if remote_hash and remote_hash != local_hash:
                GLib.idle_add(callback, remote_hash, commit_msg)
            else:
                GLib.idle_add(callback, None, None)

        except Exception as e:
            print(f"Update check failed: {e}")
            GLib.idle_add(callback, None, None)

    threading.Thread(target=_do_check, daemon=True).start()


def launch_updater_in_terminal():
    # Write a tiny installer script to /tmp and open it in whatever terminal is around.
    script_content = f"""#!/usr/bin/env bash
echo "Starting NiriMod update..."
curl -sSL https://raw.githubusercontent.com/srinivasr/nirimod/main/install.sh | bash -s -- --install
echo ""
echo "Update complete! Press Enter to close this window."
read
"""
    script_path = os.path.join(tempfile.gettempdir(), "nirimod_update.sh")
    with open(script_path, "w") as f:
        f.write(script_content)
    os.chmod(script_path, stat.S_IRWXU)

    terminals = [
        "xdg-terminal-exec",
        "gnome-terminal",
        "kgx",       # GNOME Console
        "kitty",
        "alacritty",
        "konsole",
        "foot",
        "xterm",
    ]

    for term in terminals:
        if subprocess.call(["which", term], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) == 0:
            try:
                if term == "xdg-terminal-exec":
                    subprocess.Popen([term, script_path])
                else:
                    subprocess.Popen([term, "-e", script_path])
                return
            except Exception:
                continue

    print("Could not find a suitable terminal to launch the update.")
