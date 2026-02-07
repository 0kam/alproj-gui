#!/usr/bin/env bash
set -euo pipefail

INSTALL_ROOT="$HOME/.local/opt/alproj-gui"
BIN_PATH="$HOME/.local/bin/alproj-gui"
DESKTOP_FILE="$HOME/.local/share/applications/com.alproj.gui.desktop"
ICON_FILE="$HOME/.local/share/icons/hicolor/128x128/apps/com.alproj.gui.png"

rm -f "$BIN_PATH"
rm -f "$DESKTOP_FILE"
rm -f "$ICON_FILE"
rm -rf "$INSTALL_ROOT"

if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database "$HOME/.local/share/applications" >/dev/null 2>&1 || true
fi
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
  gtk-update-icon-cache -f -t "$HOME/.local/share/icons/hicolor" >/dev/null 2>&1 || true
fi

echo "Uninstalled ALPROJ GUI from $HOME/.local"
