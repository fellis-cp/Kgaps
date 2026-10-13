#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_DIR="$HOME/.local/share/kwin/scripts/kgaps"

echo "==> Installing KGaps KWin Script..."

# Create target directory and copy files
mkdir -p "$TARGET_DIR"
cp -r "$SCRIPT_DIR/metadata.json" "$TARGET_DIR/"
cp -r "$SCRIPT_DIR/contents" "$TARGET_DIR/"

# Enable the plugin in KWin config
echo "==> Enabling KGaps in kwinrc..."
kwriteconfig6 --file kwinrc --group Plugins --key kgapsEnabled true

# Reconfigure KWin
echo "==> Reloading KWin configuration..."
for q in qdbus qdbus6 qdbus-qt6; do
    if command -v "$q" >/dev/null 2>&1; then
        "$q" org.kde.KWin /Scripting org.kde.kwin.Scripting.unloadScript "kgaps" >/dev/null 2>&1 || true
        "$q" org.kde.KWin /KWin org.kde.KWin.reconfigure >/dev/null 2>&1 || true
        break
    fi
done

# Install desktop launcher
mkdir -p "$HOME/.local/share/applications"
cp "$SCRIPT_DIR/kgaps-settings.desktop" "$HOME/.local/share/applications/"
update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true

echo ""
echo "KGaps has been successfully installed and activated!"
echo "- Open Settings App: Run ./settings.sh or launch 'KGaps Settings' from your Application Menu"
echo "- Or configure in: System Settings -> Window Management -> KWin Scripts"
