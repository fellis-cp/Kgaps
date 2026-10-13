#!/usr/bin/env bash
set -e

TARGET_DIR="$HOME/.local/share/kwin/scripts/kgaps"
DESKTOP_FILE="$HOME/.local/share/applications/kgaps-settings.desktop"

echo "==> Uninstalling KGaps..."

# Disable in kwinrc
kwriteconfig6 --file kwinrc --group Plugins --key kgapsEnabled false

# Unload from KWin memory and reconfigure
for q in qdbus qdbus6 qdbus-qt6; do
    if command -v "$q" >/dev/null 2>&1; then
        "$q" org.kde.KWin /Scripting org.kde.kwin.Scripting.unloadScript "kgaps" >/dev/null 2>&1 || true
        "$q" org.kde.KWin /KWin org.kde.KWin.reconfigure >/dev/null 2>&1 || true
        break
    fi
done

if command -v gdbus >/dev/null 2>&1; then
    gdbus call --session --dest org.kde.KWin --object-path /Scripting --method org.kde.kwin.Scripting.unloadScript "kgaps" >/dev/null 2>&1 || true
    gdbus call --session --dest org.kde.KWin --object-path /KWin --method org.kde.KWin.reconfigure >/dev/null 2>&1 || true
fi

# Remove KWin script directory/symlink
rm -rf "$TARGET_DIR"

# Remove .desktop application launcher
if [ -f "$DESKTOP_FILE" ]; then
    rm -f "$DESKTOP_FILE"
    update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true
    echo "==> Removed desktop launcher ($DESKTOP_FILE)"
fi

echo "==> KGaps has been completely uninstalled."
