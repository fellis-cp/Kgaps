# KGaps
<img width="1920" height="1080" alt="image" src="https://github.com/user-attachments/assets/1ecd505e-90a1-402b-91f7-8849254df434" />

A native KWin script for **KDE Plasma 6** (Wayland & X11) that adds customizable padding and gaps (top, bottom, left, and right) around maximized applications.

## Features

- **Per-side Gap Customization**: Set independent padding for **Top**, **Bottom**, **Left**, and **Right** (default: 15px).
- **Standalone Settings App & KDE Integration**: Configure via `kgaps-settings` (with live visual preview) or **KDE System Settings → Window Management → KWin Scripts**.
- **Wayland Native**: Resizes windows smoothly without breaking native un-maximize or fighting window clients.
- **Dock / Panel Compensation**: Automatically preserves floating panel appearance when windows are maximized.
- **Untouched Fullscreen**: Video players and games in true fullscreen remain 100% borderless/gapless (with an optional toggle and exit cooldown).
- **App Exclusions**: Customize which apps should be ignored by window class name.

## Installation

### Quick Install (One-Liner)

```bash
curl -fsSL https://raw.githubusercontent.com/fellis-cp/Kgaps/master/install.sh | bash
```

> Pass `--no-gui` if you only want the KWin script without the standalone Python settings app:
> ```bash
> curl -fsSL https://raw.githubusercontent.com/fellis-cp/Kgaps/master/install.sh | bash -s -- --no-gui
> ```

### Manual Install (Git Clone)

```bash
git clone https://github.com/fellis-cp/Kgaps.git
cd Kgaps
./install.sh
```

### Dependencies

The KWin script itself only requires **KDE Plasma 6** (`kwin`, `kwriteconfig6` / `kpackagetool6`).

For the standalone **KGaps Settings** GUI (`kgaps-settings`), install **Python 3** with **PySide6** (or **PyQt6**):

- **Arch Linux**: `sudo pacman -S pyside6`
- **Fedora**: `sudo dnf install python3-pyside6`
- **Ubuntu / Kubuntu / Debian**: `sudo apt install python3-pyside6.qtwidgets` (or `python3-pyqt6`)
- **openSUSE**: `sudo zypper install python3-pyside6`

> Ensure `~/.local/bin` is in your `PATH` to run `kgaps-settings` from a terminal. The Application Menu launcher (**KGaps Settings**) works out of the box regardless of `PATH`.

## Configuration

### 1. Dedicated Settings App (Recommended)

Launch **KGaps Settings** from your KDE Application Launcher, or run:

```bash
kgaps-settings
```

In the app, you can:
- Adjust **Top**, **Bottom**, **Left**, and **Right** padding individually or lock all sides together.
- Pick from quick presets (`0px`, `10px`, `15px`, `20px`, `30px`).
- Toggle floating panel/dock margin compensation.
- Enable auto-maximize for newly opened windows, fullscreen gap override, and fullscreen exit cooldown.
- Click **Apply Changes** to apply settings immediately in real time.

### 2. KDE System Settings

Open **System Settings → Window Management → KWin Scripts**, click the configure icon next to **KGaps**, and apply your changes.

## Updating & Uninstalling

To update, re-run `./install.sh` (or the one-line installer).

To uninstall:

```bash
./uninstall.sh
```

To also delete your saved `[Script-kgaps]` configuration from `kwinrc`:

```bash
./uninstall.sh --purge
```

## Development

```bash
make lint      # Check shell syntax and Python compilation
make test      # Run unit tests
make package   # Build kgaps-<version>.kwinscript archive
make reload    # Reload KWin script after editing contents/code/main.js
```

## License

Licensed under the **GPL-3.0-or-later** license.
