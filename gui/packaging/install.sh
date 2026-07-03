#!/usr/bin/env bash
# Entropy GUI installer. User-scope by default (no root). Pass --system for a
# system-wide install -- run that form as root (sudo ./install.sh --system).
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SYSTEM=0
[[ "${1:-}" == "--system" ]] && SYSTEM=1

check_deps() {
  local missing=()
  python3 -c "import gi; gi.require_version('Gtk','4.0'); gi.require_version('Adw','1')" 2>/dev/null \
    || missing+=(python3-gi gir1.2-gtk-4.0 gir1.2-adw-1)
  if [ ${#missing[@]} -gt 0 ]; then
    echo "Missing dependencies: ${missing[*]}"
    if [[ $SYSTEM -eq 1 ]]; then
      apt-get update && apt-get install -y "${missing[@]}"
    else
      read -rp "Install with 'sudo apt install ${missing[*]}'? (y/n): " ans
      if [[ "$ans" == "y" ]]; then
        sudo apt update && sudo apt install -y "${missing[@]}"
      else
        echo "Continuing anyway -- entropy-gui may fail to start." >&2
      fi
    fi
  fi
}
check_deps

if [[ $SYSTEM -eq 0 ]]; then
  LIB="$HOME/.local/share/entropy-gui"
  BIN="$HOME/.local/bin"
  APPS="$HOME/.local/share/applications"
  ICONS_BASE="$HOME/.local/share/icons/hicolor"
  mkdir -p "$LIB" "$BIN" "$APPS" "$ICONS_BASE"

  rm -rf "$LIB/entropy_gui"
  cp -r "$REPO_ROOT/entropy_gui" "$LIB/entropy_gui"

  cat > "$BIN/entropy-gui" <<LAUNCHER
#!/usr/bin/env bash
exec env PYTHONPATH="$LIB:\${PYTHONPATH:-}" python3 -m entropy_gui "\$@"
LAUNCHER
  chmod +x "$BIN/entropy-gui"

  install -m644 "$REPO_ROOT/packaging/com.jegly.entropygui.desktop" "$APPS/"
  cp -r "$REPO_ROOT/packaging/icons/hicolor/." "$ICONS_BASE/"
  gtk-update-icon-cache -f -t "$ICONS_BASE" 2>/dev/null || true

  echo
  echo "Installed to $BIN/entropy-gui."
  if [[ ":$PATH:" != *":$BIN:"* ]]; then
    echo "Note: $BIN is not on your PATH -- add it to ~/.bashrc or ~/.profile."
  fi
  echo "Launch from your app grid as 'Entropy', or run: entropy-gui"
else
  PREFIX="${PREFIX:-/usr/local}"
  LIB="$PREFIX/lib/entropy-gui"
  mkdir -p "$LIB"
  rm -rf "$LIB/entropy_gui"
  cp -r "$REPO_ROOT/entropy_gui" "$LIB/entropy_gui"

  cat > "$PREFIX/bin/entropy-gui" <<LAUNCHER
#!/usr/bin/env bash
exec env PYTHONPATH="$LIB:\${PYTHONPATH:-}" python3 -m entropy_gui "\$@"
LAUNCHER
  chmod +x "$PREFIX/bin/entropy-gui"

  install -Dm644 "$REPO_ROOT/packaging/com.jegly.entropygui.desktop" "$PREFIX/share/applications/com.jegly.entropygui.desktop"
  mkdir -p "$PREFIX/share/icons/hicolor"
  cp -r "$REPO_ROOT/packaging/icons/hicolor/." "$PREFIX/share/icons/hicolor/"
  gtk-update-icon-cache -f -t "$PREFIX/share/icons/hicolor" 2>/dev/null || true

  echo "System install complete under $PREFIX."
fi
