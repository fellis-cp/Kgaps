/* KGaps — KWin Script for Plasma 6
 * Adds configurable padding/gaps (top, bottom, left, right) to maximized windows.
 */

var defaultIgnored = [
    "plasmashell",
    "krunner",
    "spectacle",
    "org.kde.spectacle",
    "polkit-kde-authentication-agent-1",
    "kscreen_osd_service",
    "ksplashqml",
    "ksmserver",
    "xdg-desktop-portal-kde",
    "latte-dock"
];

var busy = {};
var reqMode = {};
var armedAt = 0;

// Configuration
var gapTop = Math.max(0, readConfig("gapTop", 15));
var gapBottom = Math.max(0, readConfig("gapBottom", 15));
var gapLeft = Math.max(0, readConfig("gapLeft", 15));
var gapRight = Math.max(0, readConfig("gapRight", 15));

var compensateDock = readConfig("compensateDock", true);
var dockMargin = Math.max(0, readConfig("dockMargin", 12));

var applyToFullscreen = readConfig("applyToFullscreen", false);
var autoMaximizeNewWindows = readConfig("autoMaximizeNewWindows", false);

var ignoredApps = (function () {
    var custom = readConfig("ignoredApps", "").toString().split(",")
        .map(function (s) { return s.trim().toLowerCase(); })
        .filter(function (s) { return s.length > 0; });
    return defaultIgnored.concat(custom);
})();

function isIgnored(win) {
    if (!win) return true;
    var cls = String(win.resourceClass || "").toLowerCase();
    var name = String(win.resourceName || "").toLowerCase();
    for (var i = 0; i < ignoredApps.length; i++) {
        var app = ignoredApps[i];
        if (cls === app || name === app || cls.indexOf(app) >= 0 || name.indexOf(app) >= 0) {
            return true;
        }
    }
    return false;
}

// Tolerance helper for Wayland fractional scaling
function near(a, b, e) {
    return Math.abs(a - b) < (e || 2);
}

function same(g, t) {
    if (!g || !t) return false;
    return near(g.x, t.x) && near(g.y, t.y) && near(g.width, t.width) && near(g.height, t.height);
}

function getGaps(win) {
    var t = gapTop;
    var b = gapBottom;
    var l = gapLeft;
    var r = gapRight;

    if (compensateDock && dockMargin > 0) {
        var s = workspace.clientArea(KWin.ScreenArea, win);
        var m = workspace.clientArea(KWin.MaximizeArea, win);

        // Panel at top
        if (m.y > s.y) {
            t += dockMargin;
        }
        // Panel at bottom
        if ((m.y + m.height) < (s.y + s.height)) {
            b += dockMargin;
        }
        // Panel at left
        if (m.x > s.x) {
            l += dockMargin;
        }
        // Panel at right
        if ((m.x + m.width) < (s.x + s.width)) {
            r += dockMargin;
        }
    }

    return { t: t, b: b, l: l, r: r };
}

function calculateTargetGeometry(win) {
    var gaps = getGaps(win);
    var area = (win.fullScreen && applyToFullscreen)
        ? workspace.clientArea(KWin.ScreenArea, win)
        : workspace.clientArea(KWin.MaximizeArea, win);

    var targetX = area.x + gaps.l;
    var targetY = area.y + gaps.t;
    var targetWidth = Math.max(100, area.width - gaps.l - gaps.r);
    var targetHeight = Math.max(100, area.height - gaps.t - gaps.b);

    return {
        x: targetX,
        y: targetY,
        width: targetWidth,
        height: targetHeight
    };
}

function isEligible(win) {
    if (!win || !win.normalWindow) return false;
    if (win.move || win.resize) return false;
    if (isIgnored(win)) return false;

    // Fullscreen handling
    if (win.fullScreen) {
        if (!applyToFullscreen) return false;
    } else {
        // Must be fully maximized (horizontal + vertical = 3)
        if (win.maximizeMode !== 3) return false;
    }

    var wid = String(win.internalId);
    if (busy[wid]) return false;
    if (reqMode[wid] !== undefined && reqMode[wid] !== 3) return false;

    return true;
}

function applyGaps(win) {
    if (!isEligible(win)) return;

    var target = calculateTargetGeometry(win);
    var current = win.frameGeometry;

    // Already at target geometry
    if (same(current, target)) return;

    // Avoid hijacking unmaximize restore animation/action:
    // Only apply if the window is currently at MaximizeArea/ScreenArea, or within reasonable gap range
    var baseArea = (win.fullScreen && applyToFullscreen)
        ? workspace.clientArea(KWin.ScreenArea, win)
        : workspace.clientArea(KWin.MaximizeArea, win);

    if (!same(current, baseArea) && !near(current.width, baseArea.width, 600)) {
        return;
    }

    var wid = String(win.internalId);
    busy[wid] = true;
    win.frameGeometry = target;
    busy[wid] = false;
}

// Preempt panel rearranges so windows don't flicker between full area and gap
function preemptRearrange(win) {
    if (Date.now() - armedAt > 15 || !isEligible(win)) return;
    var wid = String(win.internalId);
    if (reqMode[wid] !== undefined && reqMode[wid] !== 3) return;

    var target = calculateTargetGeometry(win);
    if (!same(win.frameGeometry, target)) return;

    busy[wid] = true;
    win.frameGeometry = target;
    busy[wid] = false;
}

function setupWindow(win) {
    if (!win || !win.normalWindow || isIgnored(win)) return;

    var wid = String(win.internalId);

    // Auto-maximize new windows if requested
    if (autoMaximizeNewWindows && win.maximizable && win.maximizeMode !== 3 && !win.fullScreen) {
        if (typeof win.setMaximize === "function") {
            win.setMaximize(true, true);
        }
    }

    applyGaps(win);

    win.frameGeometryChanged.connect(function () {
        if (!win.normalWindow) {
            armedAt = Date.now();
            return;
        }
        applyGaps(win);
    });

    win.frameGeometryAboutToChange.connect(function () {
        preemptRearrange(win);
    });

    win.maximizedAboutToChange.connect(function (mode) {
        reqMode[wid] = mode;
    });

    win.maximizedChanged.connect(function () {
        applyGaps(win);
    });

    win.fullScreenChanged.connect(function () {
        applyGaps(win);
    });
}

function init() {
    // Process currently opened windows
    workspace.windowList().forEach(setupWindow);

    // Process new windows when opened
    workspace.windowAdded.connect(setupWindow);

    // Clean up internal tracking when windows close
    workspace.windowRemoved.connect(function (win) {
        var wid = String(win.internalId);
        delete busy[wid];
        delete reqMode[wid];
    });

    // Screen changes / resolution changes
    function reapplyAll() {
        workspace.windowList().forEach(applyGaps);
    }

    workspace.screensChanged.connect(reapplyAll);
    workspace.virtualScreenSizeChanged.connect(reapplyAll);
    workspace.virtualScreenGeometryChanged.connect(reapplyAll);
}

init();
