#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PAYLOAD_DIR="$SCRIPT_DIR/payload"
VERSION_FILE="$SCRIPT_DIR/VERSION"

if [ ! -d "$PAYLOAD_DIR" ]; then
  echo "payload directory not found: $PAYLOAD_DIR" >&2
  exit 1
fi

if [ ! -f "$VERSION_FILE" ]; then
  echo "VERSION file not found: $VERSION_FILE" >&2
  exit 1
fi

VERSION="$(tr -d '[:space:]' < "$VERSION_FILE")"
if [ -z "$VERSION" ]; then
  echo "VERSION is empty" >&2
  exit 1
fi

INSTALL_ROOT="$HOME/.local/opt/alproj-gui"
VERSION_DIR="$INSTALL_ROOT/$VERSION"
CURRENT_LINK="$INSTALL_ROOT/current"
BIN_DIR="$HOME/.local/bin"
APP_DIR="$HOME/.local/share/applications"
ICON_DIR="$HOME/.local/share/icons/hicolor/128x128/apps"

mkdir -p "$VERSION_DIR" "$BIN_DIR" "$APP_DIR" "$ICON_DIR"

cp -a "$PAYLOAD_DIR/." "$VERSION_DIR/"
chmod +x "$VERSION_DIR/alproj-gui"
chmod +x "$VERSION_DIR/binaries/sidecar-x86_64-unknown-linux-gnu/backend-sidecar-x86_64-unknown-linux-gnu"

ln -sfn "$VERSION_DIR" "$CURRENT_LINK"
ln -sfn "$CURRENT_LINK/alproj-gui" "$BIN_DIR/alproj-gui"

DESKTOP_FILE="$APP_DIR/com.alproj.gui.desktop"
cp "$VERSION_DIR/share/applications/com.alproj.gui.desktop" "$DESKTOP_FILE"
if grep -q '^Exec=' "$DESKTOP_FILE"; then
  sed -i.bak "s|^Exec=.*$|Exec=$BIN_DIR/alproj-gui|g" "$DESKTOP_FILE"
  rm -f "$DESKTOP_FILE.bak"
else
  printf 'Exec=%s\n' "$BIN_DIR/alproj-gui" >> "$DESKTOP_FILE"
fi

cp "$VERSION_DIR/share/icons/hicolor/128x128/apps/com.alproj.gui.png" "$ICON_DIR/com.alproj.gui.png"

if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database "$APP_DIR" >/dev/null 2>&1 || true
fi
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
  gtk-update-icon-cache -f -t "$HOME/.local/share/icons/hicolor" >/dev/null 2>&1 || true
fi

cat <<EOF
Installed ALPROJ GUI $VERSION
Binary: $BIN_DIR/alproj-gui
Desktop entry: $DESKTOP_FILE
Uninstall: $SCRIPT_DIR/uninstall.sh
EOF
