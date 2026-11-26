#!/usr/bin/env python3
"""KGaps Settings GUI.

Graphical configuration tool for KGaps (KDE Plasma 6).
Allows adjusting Top, Bottom, Left, and Right gaps with real-time preview and instant apply.
"""

import argparse
import configparser
import os
import shutil
import subprocess
import sys
from pathlib import Path

APP_VERSION = "1.0.0"
SCRIPT_ID = "kgaps"
SCRIPT_GROUP = "Script-kgaps"

DEFAULT_CONFIG = {
    "gapTop": 15,
    "gapBottom": 15,
    "gapLeft": 15,
    "gapRight": 15,
    "compensateDock": True,
    "dockMargin": 12,
    "autoMaximizeNewWindows": False,
    "applyToFullscreen": False,
    "fullscreenExitCooldown": 500,
    "ignoredApps": "",
}


def get_kwinrc_path() -> Path:
    """Return the path to the user's kwinrc configuration file."""
    config_home = os.environ.get("XDG_CONFIG_HOME")
    base = Path(config_home) if config_home else Path.home() / ".config"
    return base / "kwinrc"


def _parse_config_value(raw: str, default):
    """Parse a raw string config value according to the type of default."""
    if isinstance(default, bool):
        return raw.strip().lower() == "true"
    if isinstance(default, int):
        try:
            return int(raw.strip())
        except ValueError:
            return default
    val = raw.strip()
    return val if val else default


def _read_kwinrc_fallback(key: str, default):
    """Read a key directly from kwinrc when kreadconfig6 is unavailable."""
    kwinrc = get_kwinrc_path()
    if not kwinrc.is_file():
        return default
    parser = configparser.ConfigParser(interpolation=None)
    parser.optionxform = str  # preserve case
    try:
        parser.read(kwinrc, encoding="utf-8")
        if parser.has_option(SCRIPT_GROUP, key):
            return _parse_config_value(parser.get(SCRIPT_GROUP, key), default)
    except (configparser.Error, OSError):
        pass
    return default


def _write_kwinrc_fallback(key: str, value) -> bool:
    """Write a key directly to kwinrc when kwriteconfig6 is unavailable."""
    kwinrc = get_kwinrc_path()
    parser = configparser.ConfigParser(interpolation=None)
    parser.optionxform = str
    try:
        if kwinrc.is_file():
            parser.read(kwinrc, encoding="utf-8")
        if not parser.has_section(SCRIPT_GROUP):
            parser.add_section(SCRIPT_GROUP)
        val_str = str(value).lower() if isinstance(value, bool) else str(value)
        parser.set(SCRIPT_GROUP, key, val_str)
        kwinrc.parent.mkdir(parents=True, exist_ok=True)
        with kwinrc.open("w", encoding="utf-8") as fh:
            parser.write(fh, space_around_delimiters=False)
        return True
    except (configparser.Error, OSError):
        return False


def read_kwin_config(key: str, default):
    """Read a KGaps configuration value from kwinrc via kreadconfig6 or INI fallback."""
    kread = shutil.which("kreadconfig6")
    if kread:
        try:
            res = subprocess.run(
                [kread, "--file", "kwinrc", "--group", SCRIPT_GROUP, "--key", key, "--default", str(default)],
                capture_output=True,
                text=True,
                check=False,
            )
            if res.returncode == 0:
                return _parse_config_value(res.stdout, default)
        except OSError:
            pass
    return _read_kwinrc_fallback(key, default)


def write_kwin_config(key: str, value) -> bool:
    """Write a KGaps configuration value to kwinrc via kwriteconfig6 or INI fallback."""
    val_str = str(value).lower() if isinstance(value, bool) else str(value)
    kwrite = shutil.which("kwriteconfig6")
    if kwrite:
        try:
            res = subprocess.run(
                [kwrite, "--file", "kwinrc", "--group", SCRIPT_GROUP, "--key", key, val_str],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
            if res.returncode == 0:
                return True
        except OSError:
            pass
    return _write_kwinrc_fallback(key, value)


def reconfigure_kwin() -> bool:
    """Unload KGaps and trigger KWin reconfigure so settings take effect immediately."""
    for qdbus_bin in ("qdbus", "qdbus6", "qdbus-qt6"):
        exe = shutil.which(qdbus_bin)
        if exe:
            subprocess.run(
                [exe, "org.kde.KWin", "/Scripting", "org.kde.kwin.Scripting.unloadScript", SCRIPT_ID],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
            res = subprocess.run(
                [exe, "org.kde.KWin", "/KWin", "org.kde.KWin.reconfigure"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
            return res.returncode == 0

    gdbus = shutil.which("gdbus")
    if gdbus:
        subprocess.run(
            [
                gdbus, "call", "--session", "--dest", "org.kde.KWin",
                "--object-path", "/Scripting", "--method", "org.kde.kwin.Scripting.unloadScript", SCRIPT_ID,
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        res = subprocess.run(
            [
                gdbus, "call", "--session", "--dest", "org.kde.KWin",
                "--object-path", "/KWin", "--method", "org.kde.KWin.reconfigure",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        return res.returncode == 0

    return False


def _import_qt():
    """Import Qt6 bindings, preferring PySide6 with fallback to PyQt6."""
    for backend in ("PySide6", "PyQt6"):
        try:
            qt_core = __import__(f"{backend}.QtCore", fromlist=["Qt"])
            qt_widgets = __import__(
                f"{backend}.QtWidgets",
                fromlist=[
                    "QApplication", "QMainWindow", "QWidget", "QVBoxLayout", "QHBoxLayout",
                    "QGridLayout", "QTabWidget", "QLabel", "QSpinBox", "QSlider", "QCheckBox",
                    "QPushButton", "QGroupBox", "QLineEdit", "QFrame",
                ],
            )
            qt_gui = __import__(
                f"{backend}.QtGui",
                fromlist=["QPainter", "QColor", "QPen", "QBrush", "QFont"],
            )
            return qt_core, qt_widgets, qt_gui
        except ImportError:
            continue
    return None, None, None


QtCore, QtWidgets, QtGui = _import_qt()

if QtWidgets is not None:
    Qt = QtCore.Qt
    QFrame = QtWidgets.QFrame
    QMainWindow = QtWidgets.QMainWindow
    QApplication = QtWidgets.QApplication
    QWidget = QtWidgets.QWidget
    QVBoxLayout = QtWidgets.QVBoxLayout
    QHBoxLayout = QtWidgets.QHBoxLayout
    QGridLayout = QtWidgets.QGridLayout
    QTabWidget = QtWidgets.QTabWidget
    QLabel = QtWidgets.QLabel
    QSpinBox = QtWidgets.QSpinBox
    QSlider = QtWidgets.QSlider
    QCheckBox = QtWidgets.QCheckBox
    QPushButton = QtWidgets.QPushButton
    QGroupBox = QtWidgets.QGroupBox
    QLineEdit = QtWidgets.QLineEdit
    QPainter = QtGui.QPainter
    QColor = QtGui.QColor
    QPen = QtGui.QPen
    QBrush = QtGui.QBrush
    QFont = QtGui.QFont

    class GapPreviewWidget(QFrame):
        """Visual preview showing screen bounds and inner gapped window."""

        def __init__(self, parent=None):
            super().__init__(parent)
            self.setMinimumSize(220, 160)
            self.setMaximumHeight(200)
            self.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Sunken)
            self.t = DEFAULT_CONFIG["gapTop"]
            self.b = DEFAULT_CONFIG["gapBottom"]
            self.l = DEFAULT_CONFIG["gapLeft"]
            self.r = DEFAULT_CONFIG["gapRight"]

        def update_gaps(self, t: int, b: int, l: int, r: int):
            self.t = t
            self.b = b
            self.l = l
            self.r = r
            self.update()

        def paintEvent(self, event):
            super().paintEvent(event)
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)

            w = self.width()
            h = self.height()
            pad = 14

            outer_x = pad
            outer_y = pad
            outer_w = w - (pad * 2)
            outer_h = h - (pad * 2)

            painter.setPen(QPen(QColor(80, 80, 90), 2))
            painter.setBrush(QBrush(QColor(35, 38, 41)))
            painter.drawRoundedRect(outer_x, outer_y, outer_w, outer_h, 6, 6)

            scale = 0.55
            scaled_l = min(self.l * scale, outer_w / 3.0)
            scaled_r = min(self.r * scale, outer_w / 3.0)
            scaled_t = min(self.t * scale, outer_h / 3.0)
            scaled_b = min(self.b * scale, outer_h / 3.0)

            inner_x = outer_x + scaled_l
            inner_y = outer_y + scaled_t
            inner_w = outer_w - scaled_l - scaled_r
            inner_h = outer_h - scaled_t - scaled_b

            painter.setPen(QPen(QColor(61, 174, 233), 2))
            painter.setBrush(QBrush(QColor(49, 106, 142, 170)))
            painter.drawRoundedRect(inner_x, inner_y, inner_w, inner_h, 4, 4)

            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(QColor(61, 174, 233, 220)))
            painter.drawRoundedRect(inner_x, inner_y, inner_w, min(14.0, inner_h / 4.0), 4, 4)

            painter.setPen(QPen(QColor(240, 240, 240)))
            font = QFont()
            font.setPointSize(9)
            font.setBold(True)
            painter.setFont(font)
            painter.drawText(
                int(inner_x),
                int(inner_y + 14),
                int(inner_w),
                int(inner_h - 14),
                Qt.AlignmentFlag.AlignCenter,
                f"{self.t}px / {self.b}px\n{self.l}px / {self.r}px",
            )

    class SettingsWindow(QMainWindow):
        """Main KGaps configuration window."""

        SIDES = (("top", "Top Gap:"), ("bottom", "Bottom Gap:"), ("left", "Left Gap:"), ("right", "Right Gap:"))
        PRESETS = (("Zero (0px)", 0), ("Compact (10px)", 10), ("Default (15px)", 15), ("Spacious (20px)", 20), ("Wide (30px)", 30))

        def __init__(self):
            super().__init__()
            self.setWindowTitle(f"KGaps Settings v{APP_VERSION}")
            self.resize(540, 520)
            self.syncing = False

            self.init_ui()
            self.load_values()

        def init_ui(self):
            central = QWidget()
            self.setCentralWidget(central)
            main_layout = QVBoxLayout(central)
            main_layout.setSpacing(10)
            main_layout.setContentsMargins(14, 14, 14, 14)

            self.tabs = QTabWidget()
            main_layout.addWidget(self.tabs)

            # Tab 1: Margins & Gaps
            tab_margins = QWidget()
            tab_margins_layout = QVBoxLayout(tab_margins)

            self.preview = GapPreviewWidget()
            tab_margins_layout.addWidget(self.preview)

            group_presets = QGroupBox("Quick Presets")
            presets_layout = QHBoxLayout(group_presets)
            presets_layout.setContentsMargins(8, 8, 8, 8)
            for label, val in self.PRESETS:
                btn = QPushButton(label)
                btn.clicked.connect(lambda _, v=val: self.apply_preset(v))
                presets_layout.addWidget(btn)
            tab_margins_layout.addWidget(group_presets)

            group_edges = QGroupBox("Window Padding / Margins")
            edges_layout = QGridLayout(group_edges)

            self.chk_sync = QCheckBox("Lock all edges together (same gap on all sides)")
            self.chk_sync.setChecked(True)
            self.chk_sync.toggled.connect(self.on_sync_toggled)
            edges_layout.addWidget(self.chk_sync, 0, 0, 1, 3)

            self.spins = {}
            self.sliders = {}

            for row, (side, name) in enumerate(self.SIDES, start=1):
                lbl = QLabel(name)
                spin = QSpinBox()
                spin.setRange(0, 200)
                spin.setSuffix(" px")
                spin.setValue(DEFAULT_CONFIG["gapTop"])

                slider = QSlider(Qt.Orientation.Horizontal)
                slider.setRange(0, 100)
                slider.setValue(DEFAULT_CONFIG["gapTop"])

                spin.valueChanged.connect(slider.setValue)
                slider.valueChanged.connect(spin.setValue)
                spin.valueChanged.connect(lambda val, s=side: self.on_gap_changed(s, val))

                self.spins[side] = spin
                self.sliders[side] = slider

                edges_layout.addWidget(lbl, row, 0)
                edges_layout.addWidget(spin, row, 1)
                edges_layout.addWidget(slider, row, 2)

            tab_margins_layout.addWidget(group_edges)
            self.tabs.addTab(tab_margins, "Margins & Gaps")

            # Tab 2: Docks & Panels
            tab_dock = QWidget()
            dock_layout = QVBoxLayout(tab_dock)
            group_dock = QGroupBox("Floating Panel & Dock Appearance")
            dock_form = QVBoxLayout(group_dock)

            self.chk_compensate_dock = QCheckBox("Compensate for floating panel / dock")
            self.chk_compensate_dock.setToolTip(
                "Adds margin on the dock side so Plasma floating panels keep their floating look."
            )
            dock_form.addWidget(self.chk_compensate_dock)

            dock_margin_box = QHBoxLayout()
            dock_margin_box.addWidget(QLabel("Dock extra margin:"))
            self.spin_dock_margin = QSpinBox()
            self.spin_dock_margin.setRange(0, 50)
            self.spin_dock_margin.setSuffix(" px")
            self.spin_dock_margin.setValue(DEFAULT_CONFIG["dockMargin"])
            dock_margin_box.addWidget(self.spin_dock_margin)
            dock_margin_box.addStretch()
            dock_form.addLayout(dock_margin_box)

            self.chk_compensate_dock.toggled.connect(self.spin_dock_margin.setEnabled)

            dock_layout.addWidget(group_dock)
            dock_layout.addStretch()
            self.tabs.addTab(tab_dock, "Docks & Panels")

            # Tab 3: Behavior
            tab_behavior = QWidget()
            behavior_layout = QVBoxLayout(tab_behavior)

            group_behavior = QGroupBox("Window Rules & Behavior")
            behavior_form = QVBoxLayout(group_behavior)

            self.chk_auto_maximize = QCheckBox("Automatically maximize newly opened windows (with gaps)")
            self.chk_auto_maximize.setToolTip("When enabled, windows will automatically open maximized with gaps.")
            behavior_form.addWidget(self.chk_auto_maximize)

            self.chk_fullscreen = QCheckBox("Apply gaps to fullscreen windows")
            self.chk_fullscreen.setToolTip("Keep unchecked so games, videos, and F11 apps remain truly fullscreen.")
            behavior_form.addWidget(self.chk_fullscreen)

            cooldown_box = QHBoxLayout()
            lbl_cooldown = QLabel("Fullscreen exit cooldown:")
            lbl_cooldown.setToolTip(
                "How long (in milliseconds) to wait after a window exits fullscreen\n"
                "before applying gaps. This prevents gaps from flashing during the\n"
                "exit transition (e.g. leaving YouTube or game fullscreen).\n\n"
                "Increase this if gaps briefly appear when exiting fullscreen.\n"
                "Set to 0 to disable the cooldown entirely."
            )
            self.spin_fs_cooldown = QSpinBox()
            self.spin_fs_cooldown.setRange(0, 2000)
            self.spin_fs_cooldown.setSingleStep(50)
            self.spin_fs_cooldown.setSuffix(" ms")
            self.spin_fs_cooldown.setValue(DEFAULT_CONFIG["fullscreenExitCooldown"])
            self.spin_fs_cooldown.setToolTip(lbl_cooldown.toolTip())
            cooldown_box.addWidget(lbl_cooldown)
            cooldown_box.addWidget(self.spin_fs_cooldown)
            cooldown_box.addStretch()
            behavior_form.addLayout(cooldown_box)

            self.chk_fullscreen.toggled.connect(lambda checked: self.spin_fs_cooldown.setEnabled(not checked))

            behavior_layout.addWidget(group_behavior)
            behavior_layout.addStretch()
            self.tabs.addTab(tab_behavior, "Behavior")

            # Tab 4: Exclusions
            tab_exclusions = QWidget()
            excl_layout = QVBoxLayout(tab_exclusions)
            lbl_excl = QLabel(
                "System overlays (plasmashell, krunner, spectacle, polkit) are always excluded.\n"
                "Add extra application class names below to exclude from gapping:"
            )
            lbl_excl.setWordWrap(True)
            excl_layout.addWidget(lbl_excl)

            self.edit_ignored = QLineEdit()
            self.edit_ignored.setPlaceholderText("e.g. steam, vlc, discord (comma-separated)")
            excl_layout.addWidget(self.edit_ignored)
            excl_layout.addStretch()
            self.tabs.addTab(tab_exclusions, "Exclusions")

            # Status & Action Buttons
            bottom_box = QHBoxLayout()
            self.lbl_status = QLabel("")
            self.lbl_status.setStyleSheet("color: #27ae60; font-weight: bold;")
            bottom_box.addWidget(self.lbl_status)
            bottom_box.addStretch()

            btn_reset = QPushButton("Reset Defaults")
            btn_reset.clicked.connect(self.reset_defaults)
            bottom_box.addWidget(btn_reset)

            btn_apply = QPushButton("Apply Changes")
            btn_apply.setDefault(True)
            btn_apply.setStyleSheet("background-color: #3daee9; color: white; font-weight: bold; padding: 6px 14px;")
            btn_apply.clicked.connect(self.save_and_apply)
            bottom_box.addWidget(btn_apply)

            main_layout.addLayout(bottom_box)

        def load_values(self):
            self.syncing = True
            t = read_kwin_config("gapTop", DEFAULT_CONFIG["gapTop"])
            b = read_kwin_config("gapBottom", DEFAULT_CONFIG["gapBottom"])
            l = read_kwin_config("gapLeft", DEFAULT_CONFIG["gapLeft"])
            r = read_kwin_config("gapRight", DEFAULT_CONFIG["gapRight"])

            self.spins["top"].setValue(t)
            self.spins["bottom"].setValue(b)
            self.spins["left"].setValue(l)
            self.spins["right"].setValue(r)

            self.chk_sync.setChecked(t == b == l == r)

            compensate_dock = read_kwin_config("compensateDock", DEFAULT_CONFIG["compensateDock"])
            self.chk_compensate_dock.setChecked(compensate_dock)
            self.spin_dock_margin.setValue(read_kwin_config("dockMargin", DEFAULT_CONFIG["dockMargin"]))
            self.spin_dock_margin.setEnabled(compensate_dock)

            self.chk_auto_maximize.setChecked(
                read_kwin_config("autoMaximizeNewWindows", DEFAULT_CONFIG["autoMaximizeNewWindows"])
            )
            apply_fs = read_kwin_config("applyToFullscreen", DEFAULT_CONFIG["applyToFullscreen"])
            self.chk_fullscreen.setChecked(apply_fs)
            self.spin_fs_cooldown.setValue(
                read_kwin_config("fullscreenExitCooldown", DEFAULT_CONFIG["fullscreenExitCooldown"])
            )
            self.spin_fs_cooldown.setEnabled(not apply_fs)

            self.edit_ignored.setText(read_kwin_config("ignoredApps", DEFAULT_CONFIG["ignoredApps"]))

            self.preview.update_gaps(t, b, l, r)
            self.syncing = False

        def on_sync_toggled(self, checked: bool):
            if checked:
                self.apply_preset(self.spins["top"].value())

        def on_gap_changed(self, side: str, val: int):
            if self.syncing:
                return

            if self.chk_sync.isChecked():
                self.syncing = True
                for s in ("top", "bottom", "left", "right"):
                    if s != side:
                        self.spins[s].setValue(val)
                self.syncing = False

            self.preview.update_gaps(
                self.spins["top"].value(),
                self.spins["bottom"].value(),
                self.spins["left"].value(),
                self.spins["right"].value(),
            )
            self.lbl_status.setText("")

        def apply_preset(self, val: int):
            self.syncing = True
            for s in ("top", "bottom", "left", "right"):
                self.spins[s].setValue(val)
            self.syncing = False
            self.preview.update_gaps(val, val, val, val)
            self.lbl_status.setText("")

        def reset_defaults(self):
            self.apply_preset(DEFAULT_CONFIG["gapTop"])
            self.chk_sync.setChecked(True)
            self.chk_compensate_dock.setChecked(DEFAULT_CONFIG["compensateDock"])
            self.spin_dock_margin.setValue(DEFAULT_CONFIG["dockMargin"])
            self.chk_auto_maximize.setChecked(DEFAULT_CONFIG["autoMaximizeNewWindows"])
            self.chk_fullscreen.setChecked(DEFAULT_CONFIG["applyToFullscreen"])
            self.spin_fs_cooldown.setValue(DEFAULT_CONFIG["fullscreenExitCooldown"])
            self.edit_ignored.setText(DEFAULT_CONFIG["ignoredApps"])
            self.lbl_status.setText("Reset to defaults (click Apply to save)")

        def save_and_apply(self):
            values = {
                "gapTop": self.spins["top"].value(),
                "gapBottom": self.spins["bottom"].value(),
                "gapLeft": self.spins["left"].value(),
                "gapRight": self.spins["right"].value(),
                "compensateDock": self.chk_compensate_dock.isChecked(),
                "dockMargin": self.spin_dock_margin.value(),
                "autoMaximizeNewWindows": self.chk_auto_maximize.isChecked(),
                "applyToFullscreen": self.chk_fullscreen.isChecked(),
                "fullscreenExitCooldown": self.spin_fs_cooldown.value(),
                "ignoredApps": self.edit_ignored.text().strip(),
            }

            all_saved = all(write_kwin_config(k, v) for k, v in values.items())
            reloaded = reconfigure_kwin()

            if all_saved and reloaded:
                self.lbl_status.setStyleSheet("color: #27ae60; font-weight: bold;")
                self.lbl_status.setText("✓ Settings saved & applied!")
            elif all_saved:
                self.lbl_status.setStyleSheet("color: #f39c12; font-weight: bold;")
                self.lbl_status.setText("✓ Saved, but KWin DBus reload failed.")
            else:
                self.lbl_status.setStyleSheet("color: #e74c3c; font-weight: bold;")
                self.lbl_status.setText("✗ Failed to write configuration.")


def parse_args(argv=None):
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(description="KGaps Settings GUI for KDE Plasma 6")
    parser.add_argument("--version", action="version", version=f"kgaps-settings {APP_VERSION}")
    return parser.parse_args(argv)


def main(argv=None) -> int:
    parse_args(argv)
    if QtWidgets is None:
        print(
            "Error: Neither PySide6 nor PyQt6 is installed.\n"
            "Install one of them to use the KGaps Settings GUI:\n"
            "  Arch Linux:   sudo pacman -S pyside6\n"
            "  Fedora:       sudo dnf install python3-pyside6\n"
            "  Ubuntu/Deb:   sudo apt install python3-pyside6.qtwidgets  (or python3-pyqt6)\n"
            "  openSUSE:     sudo zypper install python3-pyside6\n"
            "  pip:          pip install --user PySide6",
            file=sys.stderr,
        )
        return 1

    app = QApplication(sys.argv)
    window = SettingsWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
