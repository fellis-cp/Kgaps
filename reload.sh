#!/usr/bin/env bash
# Quick-reload KGaps via KWin DBus.

echo "==> Reloading KGaps..."

for q in qdbus qdbus6 qdbus-qt6; do
    if command -v "$q" >/dev/null 2>&1; then
        "$q" org.kde.KWin /Scripting org.kde.kwin.Scripting.unloadScript "kgaps" >/dev/null 2>&1 || true
        "$q" org.kde.KWin /KWin org.kde.KWin.reconfigure >/dev/null 2>&1 || true
        echo "==> Done! KGaps reloaded."
        exit 0
    fi
done

if command -v gdbus >/dev/null 2>&1; then
    gdbus call --session --dest org.kde.KWin --object-path /Scripting --method org.kde.kwin.Scripting.unloadScript "kgaps" >/dev/null 2>&1 || true
    gdbus call --session --dest org.kde.KWin --object-path /KWin --method org.kde.KWin.reconfigure >/dev/null 2>&1 || true
    echo "==> Done! KGaps reloaded."
    exit 0
fi

echo "Error: No DBus tool found (qdbus or gdbus)."
exit 1
