#!/usr/bin/env bash
set -euo pipefail

# Constants & Paths
VERSION="1.0.0"
INSTALL_DIR="$HOME/.local/share/nirimod"
BIN_DIR="$HOME/.local/bin"
DESKTOP_FILE_DIR="$HOME/.local/share/applications"
ICON_DIR="$HOME/.local/share/icons/hicolor/scalable/apps"
REPO_URL="https://github.com/srinivasr/nirimod"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# Helpers
info()    { echo -e "${BLUE}  ➜  ${NC}$*"; }
success() { echo -e "${GREEN}  ✓  ${NC}$*"; }
warn()    { echo -e "${YELLOW}  ⚠  ${NC}$*"; }
error()   { echo -e "${RED}  ✗  ${NC}$*" >&2; }
step()    { echo -e "\n${BOLD}${CYAN}══ $* ══${NC}"; }

pause() {
  echo -e "\n${BLUE}Press any key to continue...${NC}"
  read -n 1 -s -r < /dev/tty || true
}

ask() {
  # ask <prompt> <default>  → returns 0 for yes, 1 for no
  local prompt="$1" default="${2:-y}"
  local yn_hint
  [[ "$default" == "y" ]] && yn_hint="[Y/n]" || yn_hint="[y/N]"
  read -p "$(echo -e "${YELLOW}  ?  ${NC}${prompt} ${yn_hint}: ")" reply < /dev/tty || true
  reply="${reply:-$default}"
  [[ "$reply" =~ ^[Yy]$ ]]
}

print_banner() {
  clear
  echo -e "${BLUE}${BOLD}NiriMod Installer v${VERSION}${NC}"
  echo -e "${CYAN}GUI Configuration Manager for the Niri Wayland Compositor${NC}\n"
}

# OS Detection
detect_distro() {
  DISTRO=""
  DISTRO_PRETTY=""
  PM=""   # detected package manager

  if [ -f /etc/os-release ]; then
    # shellcheck source=/dev/null
    . /etc/os-release
    DISTRO="${ID:-}"
    DISTRO_PRETTY="${PRETTY_NAME:-$ID}"
    DISTRO_LIKE="${ID_LIKE:-}"
  fi

  # Normalize distro id using ID_LIKE fallback
  case "$DISTRO" in
    arch|manjaro|endeavouros|garuda|artix|parabola)
      PM="pacman" ;;
    fedora|rhel|centos|rocky|almalinux)
      PM="dnf" ;;
    opensuse*|sles)
      PM="zypper" ;;
    ubuntu|debian|linuxmint|pop|elementary|zorin|kali|mx|mxlinux)
      PM="apt" ;;
    *)
      # Try ID_LIKE
      if [[ "$DISTRO_LIKE" == *"arch"* ]];   then PM="pacman"
      elif [[ "$DISTRO_LIKE" == *"fedora"* ]] || [[ "$DISTRO_LIKE" == *"rhel"* ]]; then PM="dnf"
      elif [[ "$DISTRO_LIKE" == *"suse"* ]];  then PM="zypper"
      elif [[ "$DISTRO_LIKE" == *"debian"* ]] || [[ "$DISTRO_LIKE" == *"ubuntu"* ]]; then PM="apt"
      fi
      ;;
  esac

  # Verify the detected package manager actually exists
  if [ -n "$PM" ] && ! command -v "$PM" &>/dev/null; then
    PM=""
  fi

  # Last resort: probe which package manager is installed
  if [ -z "$PM" ]; then
    if   command -v pacman  &>/dev/null; then PM="pacman"
    elif command -v dnf     &>/dev/null; then PM="dnf"
    elif command -v zypper  &>/dev/null; then PM="zypper"
    elif command -v apt-get &>/dev/null; then PM="apt"
    fi
  fi

  if [ -z "$PM" ]; then
    error "Could not detect a supported package manager."
    error "Supported: pacman (Arch), dnf (Fedora/RHEL), zypper (openSUSE), apt (Debian/Ubuntu)"
    exit 1
  fi

  info "Detected: ${DISTRO_PRETTY} (package manager: ${PM})"
}

# Package Installation
install_pkgs() {
  local pkgs=("$@")
  info "Installing: ${pkgs[*]}"
  case "$PM" in
    pacman) sudo pacman -S --needed --noconfirm "${pkgs[@]}" ;;
    dnf)    sudo dnf install -y "${pkgs[@]}" ;;
    zypper) sudo zypper install -y "${pkgs[@]}" ;;
    apt)    sudo apt-get update -qq && sudo apt-get install -y "${pkgs[@]}" ;;
  esac
}

pkg_installed() {
  # Returns 0 if the package is installed, 1 otherwise
  local pkg="$1"
  case "$PM" in
    pacman) pacman -Qi "$pkg" &>/dev/null ;;
    dnf)    rpm -q "$pkg" &>/dev/null ;;
    zypper) rpm -q "$pkg" &>/dev/null ;;
    apt)    dpkg-query -W -f='${Status}' "$pkg" 2>/dev/null | grep -q "install ok installed" ;;
  esac
}

cmd_exists() { command -v "$1" &>/dev/null; }

# Dependency Resolution
#
# Maintains a list of missing packages for the current distro.
#
resolve_deps() {
  MISSING=()

  # Baseline tools
  if ! cmd_exists git; then
    case "$PM" in
      pacman) MISSING+=("git") ;;
      dnf)    MISSING+=("git") ;;
      zypper) MISSING+=("git") ;;
      apt)    MISSING+=("git") ;;
    esac
  fi


  if ! cmd_exists curl; then
    case "$PM" in
      pacman) MISSING+=("curl") ;;
      dnf)    MISSING+=("curl") ;;
      zypper) MISSING+=("curl") ;;
      apt)    MISSING+=("curl") ;;
    esac
  fi

  if ! cmd_exists python3; then
    case "$PM" in
      pacman) MISSING+=("python") ;;
      dnf)    MISSING+=("python3") ;;
      zypper) MISSING+=("python3") ;;
      apt)    MISSING+=("python3") ;;
    esac
  fi

  # GTK4
  case "$PM" in
    pacman)
      pkg_installed gtk4           || MISSING+=("gtk4") ;;
    dnf)
      pkg_installed gtk4           || MISSING+=("gtk4") ;;
    zypper)
      pkg_installed gtk4           || MISSING+=("gtk4" "gtk4-devel") ;;
    apt)
      pkg_installed libgtk-4-1    2>/dev/null || \
      pkg_installed libgtk-4-dev  2>/dev/null || \
        MISSING+=("libgtk-4-dev" "gir1.2-gtk-4.0") ;;
  esac

  # libadwaita
  case "$PM" in
    pacman)
      pkg_installed libadwaita           || MISSING+=("libadwaita") ;;
    dnf)
      pkg_installed libadwaita           || MISSING+=("libadwaita") ;;
    zypper)
      pkg_installed libadwaita-1-0       2>/dev/null || \
        MISSING+=("libadwaita" "libadwaita-devel") ;;
    apt)
      pkg_installed libadwaita-1-0       2>/dev/null || \
      pkg_installed libadwaita-1-dev     2>/dev/null || \
        MISSING+=("libadwaita-1-dev" "gir1.2-adw-1") ;;
  esac

  # PyGObject / GObject Introspection
  case "$PM" in
    pacman)
      pkg_installed python-gobject || MISSING+=("python-gobject") ;;
    dnf)
      pkg_installed python3-gobject || \
      pkg_installed python3-gobject-base || \
        MISSING+=("python3-gobject" "python3-gobject-base") ;;
    zypper)
      pkg_installed python3-gobject || \
        MISSING+=("python3-gobject" "typelib-1_0-Gtk-4_0" "typelib-1_0-Adw-1") ;;
    apt)
      pkg_installed python3-gi 2>/dev/null || \
        MISSING+=("python3-gi" "python3-gi-cairo") ;;
  esac

  # GObject typelibs (needed at runtime for gi.require_version)
  case "$PM" in
    dnf)
      rpm -q gtk4 &>/dev/null            || MISSING+=("gtk4")
      rpm -q libadwaita &>/dev/null      || MISSING+=("libadwaita")
      ;;
    zypper)
      rpm -q typelib-1_0-Gtk-4_0 &>/dev/null || MISSING+=("typelib-1_0-Gtk-4_0")
      rpm -q typelib-1_0-Adw-1   &>/dev/null || MISSING+=("typelib-1_0-Adw-1")
      ;;
    apt)
      pkg_installed gir1.2-gtk-4.0 2>/dev/null || MISSING+=("gir1.2-gtk-4.0")
      pkg_installed gir1.2-adw-1   2>/dev/null || MISSING+=("gir1.2-adw-1")
      ;;
  esac

  # Deduplicate
  if [ ${#MISSING[@]} -gt 0 ]; then
    # Remove duplicate entries
    mapfile -t MISSING < <(printf '%s\n' "${MISSING[@]}" | sort -u)
  fi
}

# Full Dependency Check
check_dependencies() {
  step "Checking System Dependencies"
  detect_distro
  resolve_deps

  if [ ${#MISSING[@]} -gt 0 ]; then
    warn "The following packages are missing:"
    for pkg in "${MISSING[@]}"; do
      echo -e "    ${RED}•${NC} $pkg"
    done
    echo ""
    if ask "Install missing packages via sudo?"; then
      install_pkgs "${MISSING[@]}"
      success "System packages installed."
    else
      error "Cannot proceed without required system packages."
      exit 1
    fi
  else
    success "All system packages are already installed."
  fi

  # Niri compositor check (optional warning)
  if ! cmd_exists niri; then
    warn "The 'niri' compositor was not found on PATH."
    warn "NiriMod requires niri to be running. Install it separately if needed."
    warn "  Arch:   sudo pacman -S niri"
    warn "  Fedora: sudo dnf install niri"
    echo ""
  fi

  # uv
  step "Checking uv (Python Environment Manager)"
  if ! cmd_exists uv; then
    warn "'uv' is not installed. It is required to manage NiriMod's Python environment."
    if ask "Install 'uv' via the official installer (astral.sh)?"; then
      info "Downloading and running the uv installer..."
      curl -LsSf https://astral.sh/uv/install.sh | sh
      # Make cargo/uv available in current session
      export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
      if [ -f "$HOME/.cargo/env" ]; then
        # shellcheck source=/dev/null
        source "$HOME/.cargo/env"
      fi
      if ! cmd_exists uv; then
        error "'uv' was installed but is not on PATH. Please restart your shell and re-run this installer."
        error "Or run:  export PATH=\"\$HOME/.local/bin:\$HOME/.cargo/bin:\$PATH\""
        exit 1
      fi
      success "'uv' installed successfully: $(uv --version)"
    else
      error "Cannot proceed without 'uv'."
      exit 1
    fi
  else
    success "'uv' is available: $(uv --version)"
  fi
}

# Download / Update Source
download_source() {
  step "Fetching Source Code"
  if [ -d "$INSTALL_DIR/.git" ]; then
    info "Updating existing installation at $INSTALL_DIR ..."
    git -C "$INSTALL_DIR" fetch --quiet origin main && \
    git -C "$INSTALL_DIR" reset --hard origin/main --quiet \
      || warn "Could not fetch latest changes (maybe no network). Continuing with existing source."
  else
    info "Cloning repository to $INSTALL_DIR ..."
    git clone "$REPO_URL" "$INSTALL_DIR"
  fi
  success "Source code is ready."
}

# Build & Wire Up
install_app() {
  step "Setting Up Python Environment"
  cd "$INSTALL_DIR"

  # PyGObject is a system package; the venv MUST see it via system site-packages.
  # We force use of the host 'python3' to ensure compatibility with system gi bindings.
  info "Creating virtual environment with system site-packages..."
  rm -rf .venv # Ensure clean state
  uv venv --system-site-packages --python python3
  uv sync --no-dev
  
  # Verification check
  if ! uv run python -c "import gi" &>/dev/null; then
    warn "Virtual environment installed, but 'gi' (PyGObject) is still not found."
    warn "This typically happens if the system bindings are missing or Python version mismatch exists."
    
    # Try to diagnose
    local host_python_ver
    host_python_ver=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    info "Host Python: $host_python_ver"
    
    if ! python3 -c "import gi" &>/dev/null; then
      error "PyGObject is NOT installed on your host system."
      error "Please install it via your package manager first (e.g., python3-gi or python-gobject)."
      exit 1
    else
      warn "PyGObject is available on host but NOT in the venv. This is unexpected."
      warn "Attempting a fallback venv creation..."
      rm -rf .venv
      uv venv --system-site-packages
      uv sync --no-dev
    fi
  fi
  success "Python environment ready and verified."

  # Launcher script
  step "Creating Launcher"
  mkdir -p "$BIN_DIR"

  # Generate launcher script
  cat > "$BIN_DIR/nirimod" << EOF
#!/usr/bin/env bash
# NiriMod launcher — auto-generated by install.sh
INSTALL_DIR="${INSTALL_DIR}"
if [ ! -d "\$INSTALL_DIR" ]; then
    echo "NiriMod is not installed at \$INSTALL_DIR. Please re-run the installer." >&2
    exit 1
fi
export PATH="\$HOME/.local/bin:\$HOME/.cargo/bin:\$PATH"
export PYTHONPATH="\$INSTALL_DIR"
cd "\$INSTALL_DIR"
exec uv run python3 -m nirimod "\$@"
EOF
  chmod +x "$BIN_DIR/nirimod"
  success "Launcher created: $BIN_DIR/nirimod"

  # Desktop entry
  step "Installing Desktop Entry"
  mkdir -p "$DESKTOP_FILE_DIR"
  mkdir -p "$ICON_DIR"

  # Copy icon if it exists in the repo
  if [ -f "$INSTALL_DIR/data/nirimod.svg" ]; then
    cp "$INSTALL_DIR/data/nirimod.svg" "$ICON_DIR/nirimod.svg"
    ICON_NAME="nirimod"
  elif [ -f "$INSTALL_DIR/data/nirimod.png" ]; then
    cp "$INSTALL_DIR/data/nirimod.png" "$HOME/.local/share/icons/hicolor/256x256/apps/nirimod.png"
    ICON_NAME="nirimod"
  else
    ICON_NAME="preferences-system"
  fi

  cat > "$DESKTOP_FILE_DIR/io.github.nirimod.desktop" << EOF
[Desktop Entry]
Version=1.0
Name=NiriMod
GenericName=Compositor Settings
Comment=GUI Configuration Manager for the Niri Wayland Compositor
Exec=${BIN_DIR}/nirimod
Icon=${ICON_NAME}
Terminal=false
Type=Application
Categories=Utility;Settings;DesktopSettings;
Keywords=compositor;windowmanager;wayland;niri;settings;config;
StartupNotify=true
StartupWMClass=nirimod
EOF

  # Refresh desktop database if available
  if cmd_exists update-desktop-database; then
    update-desktop-database "$DESKTOP_FILE_DIR" 2>/dev/null || true
  fi
  if cmd_exists gtk-update-icon-cache; then
    gtk-update-icon-cache -f -t "$HOME/.local/share/icons/hicolor" 2>/dev/null || true
  fi
  success "Desktop entry installed."

  if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
    echo ""
    warn "$BIN_DIR isn't in your PATH."
    if ask "Add it to your shell profile automatically?"; then
      for rc in "$HOME/.bashrc" "$HOME/.zshrc"; do
        if [ -f "$rc" ]; then
          if ! grep -q 'export PATH=.*\.local/bin' "$rc"; then
            echo -e '\n# nirimod' >> "$rc"
            echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$rc"
            success "Patched $rc"
          fi
        fi
      done
    else
      warn "You can run it directly: ~/.local/bin/nirimod"
    fi
  fi

  echo ""
  success "${BOLD}NiriMod ${VERSION} installed successfully!${NC}"
  info "Launch from your app menu, or run: ${CYAN}~/.local/bin/nirimod${NC}"
}

# Uninstall
uninstall() {
  step "Uninstalling NiriMod"
  warn "This will remove:"
  echo "    • $INSTALL_DIR"
  echo "    • $BIN_DIR/nirimod"
  echo "    • $DESKTOP_FILE_DIR/io.github.nirimod.desktop"
  echo ""

  if ! ask "Are you sure you want to uninstall NiriMod?"; then
    info "Uninstall cancelled."
    return
  fi

  rm -rf "$INSTALL_DIR"
  rm -f  "$BIN_DIR/nirimod"
  rm -f  "$DESKTOP_FILE_DIR/io.github.nirimod.desktop"
  rm -f  "$ICON_DIR/nirimod.svg"

  if cmd_exists update-desktop-database; then
    update-desktop-database "$DESKTOP_FILE_DIR" 2>/dev/null || true
  fi

  success "NiriMod has been uninstalled."
  pause
  exit 0
}

# Menu
main_menu() {
  while true; do
    print_banner
    echo -e "  Please select an option:\n"
    echo -e "    ${GREEN}1${NC}) Install / Update NiriMod"
    echo -e "    ${GREEN}2${NC}) Uninstall NiriMod"
    echo -e "    ${GREEN}q${NC}) Quit"
    echo ""
    read -p "$(echo -e "  ${BOLD}Enter your choice:${NC} ")" choice < /dev/tty || true

    case "$choice" in
      1)
        print_banner
        check_dependencies
        download_source
        install_app
        pause
        exit 0
        ;;
      2)
        print_banner
        uninstall
        ;;
      q|Q)
        echo -e "\n${BLUE}  Goodbye!${NC}\n"
        exit 0
        ;;
      *)
        error "Invalid option. Please choose 1, 2, or q."
        sleep 1
        ;;
    esac
  done
}

# Entry Point
# Flags:
#   --install        Download from GitHub and install (non-interactive)
#   --uninstall      Remove NiriMod (non-interactive)
case "${1:-}" in
  --install)
    print_banner
    check_dependencies
    download_source
    install_app
    exit 0
    ;;

  --uninstall)
    print_banner
    uninstall
    ;;
  "")
    main_menu
    ;;
  *)
    error "Unknown option: $1"
    echo "Usage: $0 [--install | --uninstall]"
    exit 1
    ;;
esac
