# ALPROJ GUI Linux Package

This archive contains a user-local install package for x86_64 Linux.

## Install

```bash
tar -xzf ALPROJ.GUI_<version>_linux_x86_64.tar.gz
cd alproj-gui-linux-x86_64
./install.sh
```

The app is installed under `~/.local/opt/alproj-gui` and exposed as:

- `~/.local/bin/alproj-gui`
- desktop entry: `~/.local/share/applications/com.alproj.gui.desktop`

## Uninstall

```bash
./uninstall.sh
```

## Update

Extract a newer archive and run:

```bash
./update.sh
```
