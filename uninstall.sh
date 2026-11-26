#!/usr/bin/env bash
set -euo pipefail

SCRIPT_ID="kgaps"
XDG_DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
TARGET_DIR="$XDG_DATA_HOME/kwin/scripts/$SCRIPT_ID"
APP_DATA_DIR="$XDG_DATA_HOME/kgaps"
BIN_LAUNCHER="$HOME/.local/bin/kgaps-settings"
DESKTOP_FILE="$XDG_DATA_HOME/applications/kgaps-settings.desktop"

PURGE=false

usage() {
    cat <<EOF
Usage: $(basename "$0") [OPTIONS]

Uninstall KGaps KWin script and settings GUI.

Options:
  --purge     Also remove saved [Script-kgaps] configuration from kwinrc
  -h, --help  Show this help message
EOF
}

while [ "$#" -gt 0 ]; do
    case "$1" in
        --purge)
            PURGE=true
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

echo "==> Uninstalling KGaps..."

if command -v kwriteconfig6 >/dev/null 2>&1; then
    kwriteconfig6 --file kwinrc --group Plugins --key kgapsEnabled false
    if [ "$PURGE" = true ]; then
        kwriteconfig6 --file kwinrc --group Plugins --key kgapsEnabled --delete || true
        kwriteconfig6 --file kwinrc --group Script-kgaps --delete-group || true
    fi
fi

for q in qdbus qdbus6 qdbus-qt6; do
    if command -v "$q" >/dev/null 2>&1; then
        "$q" org.kde.KWin /Scripting org.kde.kwin.Scripting.unloadScript "$SCRIPT_ID" >/dev/null 2>&1 || true
        "$q" org.kde.KWin /KWin org.kde.KWin.reconfigure >/dev/null 2>&1 || true
        break
    fi
done

if command -v gdbus >/dev/null 2>&1; then
    gdbus call --session --dest org.kde.KWin --object-path /Scripting --method org.kde.kwin.Scripting.unloadScript "$SCRIPT_ID" >/dev/null 2>&1 || true
    gdbus call --session --dest org.kde.KWin --object-path /KWin --method org.kde.KWin.reconfigure >/dev/null 2>&1 || true
fi

if command -v kpackagetool6 >/dev/null 2>&1; then
    kpackagetool6 -t KWin/Script -r "$SCRIPT_ID" >/dev/null 2>&1 || true
fi
rm -rf "$TARGET_DIR"

if [ -f "$DESKTOP_FILE" ]; then
    rm -f "$DESKTOP_FILE"
    update-desktop-database "$XDG_DATA_HOME/applications" >/dev/null 2>&1 || true
    echo "==> Removed desktop launcher ($DESKTOP_FILE)"
fi

if [ -f "$BIN_LAUNCHER" ]; then
    rm -f "$BIN_LAUNCHER"
    echo "==> Removed CLI launcher ($BIN_LAUNCHER)"
fi

if [ -d "$APP_DATA_DIR" ]; then
    rm -rf "$APP_DATA_DIR"
    echo "==> Removed app data ($APP_DATA_DIR)"
fi

echo "==> KGaps has been completely uninstalled."
