#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/fellis-cp/Kgaps.git"
ARCHIVE_URL="https://github.com/fellis-cp/Kgaps/archive/refs/heads/master.tar.gz"
SCRIPT_ID="kgaps"

XDG_DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
BIN_DIR="$HOME/.local/bin"
APP_DATA_DIR="$XDG_DATA_HOME/kgaps"
KWIN_SCRIPTS_DIR="$XDG_DATA_HOME/kwin/scripts"
TARGET_DIR="$KWIN_SCRIPTS_DIR/$SCRIPT_ID"
DESKTOP_DIR="$XDG_DATA_HOME/applications"

INSTALL_GUI=true
TMP_DIR=""

usage() {
    cat <<EOF
Usage: $(basename "$0") [OPTIONS]

Install KGaps KWin script and settings GUI for KDE Plasma 6.

Options:
  --no-gui      Install only the KWin script (skip settings GUI and launcher)
  --uninstall   Uninstall KGaps
  -h, --help    Show this help message
EOF
}

cleanup() {
    if [ -n "$TMP_DIR" ] && [ -d "$TMP_DIR" ]; then
        rm -rf "$TMP_DIR"
    fi
}
trap cleanup EXIT

while [ "$#" -gt 0 ]; do
    case "$1" in
        --no-gui)
            INSTALL_GUI=false
            ;;
        --uninstall)
            SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
            if [ -f "$SCRIPT_DIR/uninstall.sh" ]; then
                exec bash "$SCRIPT_DIR/uninstall.sh"
            fi
            echo "Error: uninstall.sh not found in $SCRIPT_DIR" >&2
            exit 1
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1" >&2
            usage >&2
            exit 1
            ;;
    esac
    shift
done

reload_kwin() {
    for q in qdbus qdbus6 qdbus-qt6; do
        if command -v "$q" >/dev/null 2>&1; then
            "$q" org.kde.KWin /Scripting org.kde.kwin.Scripting.unloadScript "$SCRIPT_ID" >/dev/null 2>&1 || true
            "$q" org.kde.KWin /KWin org.kde.KWin.reconfigure >/dev/null 2>&1 || true
            return 0
        fi
    done
    if command -v gdbus >/dev/null 2>&1; then
        gdbus call --session --dest org.kde.KWin --object-path /Scripting --method org.kde.kwin.Scripting.unloadScript "$SCRIPT_ID" >/dev/null 2>&1 || true
        gdbus call --session --dest org.kde.KWin --object-path /KWin --method org.kde.KWin.reconfigure >/dev/null 2>&1 || true
        return 0
    fi
    return 1
}

# Resolve source directory (support both local repo and `curl ... | bash`)
SOURCE_DIR=""
if [ -n "${BASH_SOURCE[0]:-}" ] && [ -f "${BASH_SOURCE[0]}" ]; then
    CANDIDATE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    if [ -f "$CANDIDATE_DIR/metadata.json" ] && [ -d "$CANDIDATE_DIR/contents" ]; then
        SOURCE_DIR="$CANDIDATE_DIR"
    fi
fi

if [ -z "$SOURCE_DIR" ]; then
    echo "==> Downloading KGaps source..."
    TMP_DIR="$(mktemp -d)"
    if command -v git >/dev/null 2>&1; then
        git clone --depth 1 "$REPO_URL" "$TMP_DIR/Kgaps"
        SOURCE_DIR="$TMP_DIR/Kgaps"
    elif command -v curl >/dev/null 2>&1; then
        curl -fsSL "$ARCHIVE_URL" | tar -xz -C "$TMP_DIR"
        SOURCE_DIR="$TMP_DIR/Kgaps-master"
    elif command -v wget >/dev/null 2>&1; then
        wget -qO- "$ARCHIVE_URL" | tar -xz -C "$TMP_DIR"
        SOURCE_DIR="$TMP_DIR/Kgaps-master"
    else
        echo "Error: git, curl, or wget is required to download KGaps." >&2
        exit 1
    fi
fi

echo "==> Installing KGaps KWin Script..."

if command -v kpackagetool6 >/dev/null 2>&1; then
    if kpackagetool6 -t KWin/Script -s "$SCRIPT_ID" >/dev/null 2>&1; then
        kpackagetool6 -t KWin/Script -u "$SOURCE_DIR"
    else
        kpackagetool6 -t KWin/Script -i "$SOURCE_DIR"
    fi
else
    mkdir -p "$TARGET_DIR"
    cp "$SOURCE_DIR/metadata.json" "$TARGET_DIR/"
    rm -rf "$TARGET_DIR/contents"
    cp -r "$SOURCE_DIR/contents" "$TARGET_DIR/"
fi

if command -v kwriteconfig6 >/dev/null 2>&1; then
    echo "==> Enabling KGaps in kwinrc..."
    kwriteconfig6 --file kwinrc --group Plugins --key kgapsEnabled true
else
    echo "Warning: kwriteconfig6 not found. Enable KGaps manually in:"
    echo "  System Settings -> Window Management -> KWin Scripts"
fi

echo "==> Reloading KWin configuration..."
if ! reload_kwin; then
    echo "Warning: No DBus tool (qdbus/gdbus) found. Log out and back in or reload KWin manually."
fi

if [ "$INSTALL_GUI" = true ]; then
    echo "==> Installing KGaps Settings GUI..."
    mkdir -p "$APP_DATA_DIR" "$BIN_DIR" "$DESKTOP_DIR"
    cp "$SOURCE_DIR/kgaps_settings.py" "$APP_DATA_DIR/kgaps_settings.py"
    chmod +x "$APP_DATA_DIR/kgaps_settings.py"

    cat > "$BIN_DIR/kgaps-settings" <<EOF
#!/usr/bin/env bash
exec python3 "$APP_DATA_DIR/kgaps_settings.py" "\$@"
EOF
    chmod +x "$BIN_DIR/kgaps-settings"

    cat > "$DESKTOP_DIR/kgaps-settings.desktop" <<EOF
[Desktop Entry]
Name=KGaps Settings
Comment=Configure window padding and gaps for KDE Plasma 6
Exec=$BIN_DIR/kgaps-settings
Icon=preferences-system-windows-script-test
Terminal=false
Type=Application
Categories=Settings;DesktopSettings;Qt;KDE;
StartupNotify=true
EOF
    update-desktop-database "$DESKTOP_DIR" >/dev/null 2>&1 || true

    # Check Python Qt bindings
    if ! command -v python3 >/dev/null 2>&1 || ! python3 -c "import PySide6" >/dev/null 2>&1 && ! python3 -c "import PyQt6" >/dev/null 2>&1; then
        echo ""
        echo "Note: Python Qt6 bindings (PySide6 or PyQt6) were not detected."
        echo "To use the standalone KGaps Settings GUI, install one of:"
        echo "  Arch Linux:   sudo pacman -S pyside6"
        echo "  Fedora:       sudo dnf install python3-pyside6"
        echo "  Ubuntu/Deb:   sudo apt install python3-pyside6.qtwidgets  (or python3-pyqt6)"
        echo "  openSUSE:     sudo zypper install python3-pyside6"
        echo "You can still configure KGaps via System Settings -> Window Management -> KWin Scripts."
    fi
fi

echo ""
echo "KGaps has been successfully installed and activated!"
if [ "$INSTALL_GUI" = true ]; then
    echo "- Open Settings App: Run 'kgaps-settings' (or '$BIN_DIR/kgaps-settings') or launch 'KGaps Settings' from your Application Menu"
fi
echo "- Or configure in: System Settings -> Window Management -> KWin Scripts"
