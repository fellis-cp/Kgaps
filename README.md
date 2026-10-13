# KGaps

<img width="1920" height="1080" alt="image" src="https://github.com/user-attachments/assets/4f041bda-82ce-4011-bf91-8c3e25f9e0cd" />


A native KWin script for **KDE Plasma 6** (Wayland & X11) that adds customizable padding and gaps (top, bottom, left, and right) around maximized applications.

## Features

- **Per-side Gap Customization**: Set independent padding for **Top**, **Bottom**, **Left**, and **Right** (default: 15px).
- **GUI Settings**: Full integration into **KDE System Settings → Window Management → KWin Scripts**.
- **Wayland Native**: Resizes windows smoothly without breaking native un-maximize or fighting window clients.
- **Dock / Panel Compensation**: Automatically preserves floating panel appearance when windows are maximized.
- **Untouched Fullscreen**: Video players and games in true fullscreen remain 100% borderless/gapless (with an optional toggle to gap them if desired).
- **App Exclusions**: Customize which apps should be ignored.

## Installation

Run the installation script:
```bash
chmod +x install.sh reload.sh uninstall.sh
./install.sh
```

## Configuration

You can configure KGaps in two easy ways:

### 1. Dedicated Settings App (Recommended)
Launch the graphical settings tool to adjust padding with live preview:
```bash
./settings.sh
```
Or open **KGaps Settings** directly from your KDE Application Launcher (Start Menu).

In the app, you can:
- Adjust **Top**, **Bottom**, **Left**, and **Right** padding individually or lock all sides together.
- Pick from quick presets (0px, 10px, 15px, 20px, 30px).
- Toggle floating panel/dock margin compensation.
- Enable auto-maximize for newly opened windows or padding on fullscreen apps.
- Click **Apply Changes** to apply the new sizes immediately in real-time.


## Removal

To uninstall KGaps:
```bash
./uninstall.sh
```
