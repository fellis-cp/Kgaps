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
// Tracks the timestamp when a window last exited the fullscreen state.
// Used to suppress gap application during the brief transition period.
var fullscreenExitAt = {};

// Configuration
var gapTop = Math.max(0, readConfig("gapTop", 15));
var gapBottom = Math.max(0, readConfig("gapBottom", 15));
var gapLeft = Math.max(0, readConfig("gapLeft", 15));
var gapRight = Math.max(0, readConfig("gapRight", 15));

var compensateDock = readConfig("compensateDock", true);
var dockMargin = Math.max(0, readConfig("dockMargin", 12));

var applyToFullscreen = readConfig("applyToFullscreen", false);
var applyToQuickTile = readConfig("applyToQuickTile", true);
var quickTileInnerGap = Math.max(0, readConfig("quickTileInnerGap", 10));
var autoMaximizeNewWindows = readConfig("autoMaximizeNewWindows", false);
// How long (ms) after a fullscreen exit to suppress gap application.
// Covers panelless screens and geometry events during the exit transition.
var FULLSCREEN_EXIT_COOLDOWN = Math.max(0, readConfig("fullscreenExitCooldown", 500));

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

function isQuickTiled(win) {
    if (!win) return false;
    if (win.tile) return true;
    var mode = win.quickTileMode || 0;
    if (mode > 0 && mode !== 15) return true;
    return false;
}

function getBaseArea(win) {
    if (win.fullScreen && applyToFullscreen) {
        return workspace.clientArea(KWin.ScreenArea, win);
    }

    var maxArea = workspace.clientArea(KWin.MaximizeArea, win);

    if (applyToQuickTile && isQuickTiled(win)) {
        if (win.tile && win.tile.absoluteGeometry && win.tile.absoluteGeometry.width > 0) {
            return win.tile.absoluteGeometry;
        }

        var mode = win.quickTileMode || 0;
        if (mode > 0 && mode !== 15) {
            var halfW = Math.round(maxArea.width / 2);
            var halfH = Math.round(maxArea.height / 2);
            var x = maxArea.x;
            var y = maxArea.y;
            var w = maxArea.width;
            var h = maxArea.height;

            if (mode & 1) { // Left
                x = maxArea.x;
                w = (mode & 2) ? maxArea.width : halfW;
            } else if (mode & 2) { // Right
                x = maxArea.x + halfW;
                w = maxArea.width - halfW;
            }

            if (mode & 4) { // Top
                y = maxArea.y;
                h = (mode & 8) ? maxArea.height : halfH;
            } else if (mode & 8) { // Bottom
                y = maxArea.y + halfH;
                h = maxArea.height - halfH;
            }

            return { x: x, y: y, width: w, height: h };
        }
    }

    return maxArea;
}

function calculateTargetGeometry(win) {
    var baseArea = getBaseArea(win);
    var gaps = getGaps(win);
    var maxArea = workspace.clientArea(KWin.MaximizeArea, win);

    var padL, padR, padT, padB;

    if (applyToQuickTile && isQuickTiled(win)) {
        var halfInner = Math.floor(quickTileInnerGap / 2);
        var otherHalfInner = quickTileInnerGap - halfInner;

        var isOuterLeft = near(baseArea.x, maxArea.x, 4);
        var isOuterRight = near(baseArea.x + baseArea.width, maxArea.x + maxArea.width, 4);
        var isOuterTop = near(baseArea.y, maxArea.y, 4);
        var isOuterBottom = near(baseArea.y + baseArea.height, maxArea.y + maxArea.height, 4);

        padL = isOuterLeft ? gaps.l : halfInner;
        padR = isOuterRight ? gaps.r : otherHalfInner;
        padT = isOuterTop ? gaps.t : halfInner;
        padB = isOuterBottom ? gaps.b : otherHalfInner;
    } else {
        padL = gaps.l;
        padR = gaps.r;
        padT = gaps.t;
        padB = gaps.b;
    }

    var targetX = baseArea.x + padL;
    var targetY = baseArea.y + padT;
    var targetWidth = Math.max(100, baseArea.width - padL - padR);
    var targetHeight = Math.max(100, baseArea.height - padT - padB);

    return {
        x: targetX,
        y: targetY,
        width: targetWidth,
        height: targetHeight
    };
}

// Returns true when a maximized window is covering the entire physical screen
// (i.e. acting as a fullscreen window without using the fullscreen API).
//
// IMPORTANT: this check is only meaningful when panels ARE present. When there
// are no panels, MaximizeArea == ScreenArea, so every maximized window would
// match — we return false in that case and fall back to the cooldown check.
function isOverlappingFullscreen(win) {
    var screen = workspace.clientArea(KWin.ScreenArea, win);
    var maxArea = workspace.clientArea(KWin.MaximizeArea, win);

    // No panels: can't distinguish maximize-covering-screen from true fullscreen via geometry.
    var panelsPresent =
        !near(screen.x, maxArea.x, 2) || !near(screen.y, maxArea.y, 2) ||
        !near(screen.width, maxArea.width, 2) || !near(screen.height, maxArea.height, 2);
    if (!panelsPresent) return false;

    // Panels are present: if the window still covers the full ScreenArea
    // (i.e. it's going over/under the panels), it's acting fullscreen.
    var geo = win.frameGeometry;
    return near(geo.x, screen.x, 4) &&
           near(geo.y, screen.y, 4) &&
           near(geo.width, screen.width, 4) &&
           near(geo.height, screen.height, 4);
}


function isEligible(win) {
    if (!win || !win.normalWindow) return false;
    if (win.move || win.resize) return false;
    if (isIgnored(win)) return false;

    var wid = String(win.internalId);

    // Fullscreen handling
    if (win.fullScreen) {
        if (!applyToFullscreen) return false;
    } else {
        var quickTiled = applyToQuickTile && isQuickTiled(win);
        if (!quickTiled) {
            // Must be fully maximized (horizontal + vertical = 3)
            if (win.maximizeMode !== 3) return false;

            if (!applyToFullscreen) {
                // Strategy 1 — geometry check (works when panels are present):
                // Skip windows that cover the entire physical screen even though
                // win.fullScreen is false (e.g. games via maximize, or a browser
                // mid-transition while exiting HTML5 fullscreen with panels visible).
                if (isOverlappingFullscreen(win)) return false;

                // Strategy 2 — cooldown (works on panelless screens and catches any
                // geometry events that slip through before the window shrinks back):
                // For a short window after exiting fullscreen, don't apply gaps.
                if (fullscreenExitAt[wid] && Date.now() - fullscreenExitAt[wid] < FULLSCREEN_EXIT_COOLDOWN) return false;
            }

            if (reqMode[wid] !== undefined && reqMode[wid] !== 3) return false;
        }
    }

    if (busy[wid]) return false;

    return true;
}

function applyGaps(win) {
    if (!isEligible(win)) return;

    var target = calculateTargetGeometry(win);
    var current = win.frameGeometry;

    // Already at target geometry
    if (same(current, target)) return;

    // Avoid hijacking unmaximize restore animation/action:
    // Only apply if the window is currently at baseArea, or within reasonable gap range
    var baseArea = getBaseArea(win);

    if (!same(current, baseArea) && !near(current.width, baseArea.width, 600)) {
        return;
    }

    var wid = String(win.internalId);
    busy[wid] = true;
    try {
        win.frameGeometry = target;
    } finally {
        busy[wid] = false;
    }
}

// Preempt panel rearranges so windows don't flicker between full area and gap
function preemptRearrange(win) {
    if (Date.now() - armedAt > 15 || !isEligible(win)) return;
    var wid = String(win.internalId);
    if (!isQuickTiled(win) && reqMode[wid] !== undefined && reqMode[wid] !== 3) return;

    var target = calculateTargetGeometry(win);
    if (!same(win.frameGeometry, target)) return;

    busy[wid] = true;
    try {
        win.frameGeometry = target;
    } finally {
        busy[wid] = false;
    }
}

// Connects all KWin signals for a window and does an initial gap apply.
// Does NOT auto-maximize — safe to call on already-open windows.
function connectWindow(win) {
    if (!win || !win.normalWindow || isIgnored(win)) return;

    var wid = String(win.internalId);

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
        if (win.maximizeMode === 3) {
            reqMode[wid] = 3;
        } else {
            delete reqMode[wid];
        }
        applyGaps(win);
    });

    if (typeof win.quickTileModeChanged !== "undefined") {
        win.quickTileModeChanged.connect(function () {
            delete reqMode[wid];
            applyGaps(win);
        });
    }

    if (typeof win.tileChanged !== "undefined") {
        win.tileChanged.connect(function () {
            delete reqMode[wid];
            applyGaps(win);
        });
    }

    win.fullScreenChanged.connect(function () {
        if (!win.fullScreen) {
            fullscreenExitAt[wid] = Date.now();
        } else {
            delete fullscreenExitAt[wid];
        }
        applyGaps(win);
    });
}

// Called only for brand-new windows (windowAdded signal).
// Optionally auto-maximizes them before connecting signals.
function setupWindow(win) {
    if (!win || !win.normalWindow || isIgnored(win)) return;

    // Auto-maximize only truly new windows when the option is enabled.
    if (autoMaximizeNewWindows && win.maximizable && win.maximizeMode !== 3 && !win.fullScreen) {
        if (typeof win.setMaximize === "function") {
            win.setMaximize(true, true);
        }
    }

    connectWindow(win);
}

function init() {
    // Re-apply gaps to currently open windows WITHOUT auto-maximizing them.
    // (connectWindow skips the auto-maximize logic, so reloading KGaps settings
    // never forcibly maximizes windows the user had open in a smaller state.)
    workspace.windowList().forEach(connectWindow);

    // Only newly opened windows go through the full setupWindow (which may auto-maximize).
    workspace.windowAdded.connect(setupWindow);

    // Clean up internal tracking when windows close
    workspace.windowRemoved.connect(function (win) {
        if (!win) return;
        var wid = String(win.internalId);
        delete busy[wid];
        delete reqMode[wid];
        delete fullscreenExitAt[wid];
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
