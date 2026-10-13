#!/usr/bin/env python3
"""
KGaps Settings GUI
A dedicated graphical configuration tool for KGaps (KDE Plasma 6).
Allows adjusting Top, Bottom, Left, and Right gaps in real-time with instant apply.
"""

import sys
import subprocess
from pathlib import Path
from PySide6.QtCore import Qt, QSettings
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QTabWidget, QLabel, QSpinBox, QSlider, QCheckBox,
    QPushButton, QGroupBox, QLineEdit, QListWidget, QListWidgetItem,
    QFrame, QMessageBox, QSpacerItem, QSizePolicy
)
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QFont, QIcon

KWINRC_PATH = Path.home() / ".config" / "kwinrc"
SCRIPT_GROUP = "Script-kgaps"


def run_cmd(args):
    try:
        subprocess.run(args, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass


def reconfigure_kwin():
    # In KWin, calling unloadScript on the script ID followed by reconfigure
    # forces KWin to unload and re-execute the script afresh with the new config values.
    for q in ["qdbus", "qdbus6", "qdbus-qt6"]:
        res = subprocess.run(["which", q], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if res.returncode == 0:
            subprocess.run([q, "org.kde.KWin", "/Scripting", "org.kde.kwin.Scripting.unloadScript", "kgaps"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run([q, "org.kde.KWin", "/KWin", "reconfigure"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return
    # Fallback to gdbus
    subprocess.run(["gdbus", "call", "--session", "--dest", "org.kde.KWin", "--object-path", "/Scripting", "--method", "org.kde.kwin.Scripting.unloadScript", "kgaps"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(["gdbus", "call", "--session", "--dest", "org.kde.KWin", "--object-path", "/KWin", "--method", "org.kde.KWin.reconfigure"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def read_kwin_config(key, default):
    res = subprocess.run(
        ["kreadconfig6", "--file", "kwinrc", "--group", SCRIPT_GROUP, "--key", key, "--default", str(default)],
        capture_output=True, text=True
    )
    val = res.stdout.strip()
    if isinstance(default, bool):
        return val.lower() == "true"
    elif isinstance(default, int):
        try:
            return int(val)
        except ValueError:
            return default
    return val if val else default


def write_kwin_config(key, value):
    val_str = str(value).lower() if isinstance(value, bool) else str(value)
    subprocess.run(["kwriteconfig6", "--file", "kwinrc", "--group", SCRIPT_GROUP, "--key", key, val_str])


class GapPreviewWidget(QFrame):
    """Visual preview showing screen bounds and inner gapped window."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(220, 160)
        self.setMaximumHeight(200)
        self.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Sunken)
        self.t = 15
        self.b = 15
        self.l = 15
        self.r = 15

    def update_gaps(self, t, b, l, r):
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

        # Outer monitor / screen frame
        outer_rect_x = pad
        outer_rect_y = pad
        outer_rect_w = w - (pad * 2)
        outer_rect_h = h - (pad * 2)

        # Draw Monitor representation
        painter.setPen(QPen(QColor(80, 80, 90), 2))
        painter.setBrush(QBrush(QColor(35, 38, 41)))
        painter.drawRoundedRect(outer_rect_x, outer_rect_y, outer_rect_w, outer_rect_h, 6, 6)

        # Scale factor for gaps in preview
        scale = 0.55
        scaled_l = min(self.l * scale, outer_rect_w / 3.0)
        scaled_r = min(self.r * scale, outer_rect_w / 3.0)
        scaled_t = min(self.t * scale, outer_rect_h / 3.0)
        scaled_b = min(self.b * scale, outer_rect_h / 3.0)

        inner_x = outer_rect_x + scaled_l
        inner_y = outer_rect_y + scaled_t
        inner_w = outer_rect_w - scaled_l - scaled_r
        inner_h = outer_rect_h - scaled_t - scaled_b

        # Draw Window representation
        painter.setPen(QPen(QColor(61, 174, 233), 2))
        painter.setBrush(QBrush(QColor(49, 106, 142, 170)))
        painter.drawRoundedRect(inner_x, inner_y, inner_w, inner_h, 4, 4)

        # Window titlebar mock
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(61, 174, 233, 220)))
        painter.drawRoundedRect(inner_x, inner_y, inner_w, min(14.0, inner_h / 4.0), 4, 4)

        # Label in center
        painter.setPen(QPen(QColor(240, 240, 240)))
        font = QFont()
        font.setPointSize(9)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(
            int(inner_x), int(inner_y + 14), int(inner_w), int(inner_h - 14),
            Qt.AlignmentFlag.AlignCenter, f"{self.t}px / {self.b}px\n{self.l}px / {self.r}px"
        )


class SettingsWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("KGaps Settings")
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

        # Tabs
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)

        # Tab 1: Margins
        tab_margins = QWidget()
        tab_margins_layout = QVBoxLayout(tab_margins)

        # Visual preview
        self.preview = GapPreviewWidget()
        tab_margins_layout.addWidget(self.preview)

        # Presets
        group_presets = QGroupBox("Quick Presets")
        presets_layout = QHBoxLayout(group_presets)
        presets_layout.setContentsMargins(8, 8, 8, 8)
        for label, val in [("Zero (0px)", 0), ("Compact (10px)", 10), ("Default (15px)", 15), ("Spacious (20px)", 20), ("Wide (30px)", 30)]:
            btn = QPushButton(label)
            btn.clicked.connect(lambda _, v=val: self.apply_preset(v))
            presets_layout.addWidget(btn)
        tab_margins_layout.addWidget(group_presets)

        # Edge Margins Box
        group_edges = QGroupBox("Window Padding / Margins")
        edges_layout = QGridLayout(group_edges)

        # Sync checkbox
        self.chk_sync = QCheckBox("Lock all edges together (same gap on all sides)")
        self.chk_sync.setChecked(True)
        self.chk_sync.toggled.connect(self.on_sync_toggled)
        edges_layout.addWidget(self.chk_sync, 0, 0, 1, 3)

        # Spinboxes and sliders
        self.spins = {}
        self.sliders = {}

        for row, (side, name) in enumerate([("top", "Top Gap:"), ("bottom", "Bottom Gap:"), ("left", "Left Gap:"), ("right", "Right Gap:")], start=1):
            lbl = QLabel(name)
            spin = QSpinBox()
            spin.setRange(0, 200)
            spin.setSuffix(" px")
            spin.setValue(15)

            slider = QSlider(Qt.Orientation.Horizontal)
            slider.setRange(0, 100)
            slider.setValue(15)

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

        # Tab 2: Dock & Panels
        tab_dock = QWidget()
        dock_layout = QVBoxLayout(tab_dock)
        group_dock = QGroupBox("Floating Panel & Dock Appearance")
        dock_form = QVBoxLayout(group_dock)

        self.chk_compensate_dock = QCheckBox("Compensate for floating panel / dock")
        self.chk_compensate_dock.setToolTip("Adds margin on the dock side so Plasma floating panels keep their floating look.")
        dock_form.addWidget(self.chk_compensate_dock)

        dock_margin_box = QHBoxLayout()
        dock_margin_box.addWidget(QLabel("Dock extra margin:"))
        self.spin_dock_margin = QSpinBox()
        self.spin_dock_margin.setRange(0, 50)
        self.spin_dock_margin.setSuffix(" px")
        self.spin_dock_margin.setValue(12)
        dock_margin_box.addWidget(self.spin_dock_margin)
        dock_margin_box.addStretch()
        dock_form.addLayout(dock_margin_box)

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
        t = read_kwin_config("gapTop", 15)
        b = read_kwin_config("gapBottom", 15)
        l = read_kwin_config("gapLeft", 15)
        r = read_kwin_config("gapRight", 15)

        self.spins["top"].setValue(t)
        self.spins["bottom"].setValue(b)
        self.spins["left"].setValue(l)
        self.spins["right"].setValue(r)

        self.chk_sync.setChecked(t == b == l == r)
        self.chk_compensate_dock.setChecked(read_kwin_config("compensateDock", True))
        self.spin_dock_margin.setValue(read_kwin_config("dockMargin", 12))
        self.chk_auto_maximize.setChecked(read_kwin_config("autoMaximizeNewWindows", False))
        self.chk_fullscreen.setChecked(read_kwin_config("applyToFullscreen", False))
        self.edit_ignored.setText(read_kwin_config("ignoredApps", ""))

        self.preview.update_gaps(t, b, l, r)
        self.syncing = False

    def on_sync_toggled(self, checked):
        if checked:
            master_val = self.spins["top"].value()
            self.apply_preset(master_val)

    def on_gap_changed(self, side, val):
        if self.syncing:
            return

        if self.chk_sync.isChecked():
            self.syncing = True
            for s in ["top", "bottom", "left", "right"]:
                if s != side:
                    self.spins[s].setValue(val)
            self.syncing = False

        self.preview.update_gaps(
            self.spins["top"].value(),
            self.spins["bottom"].value(),
            self.spins["left"].value(),
            self.spins["right"].value()
        )
        self.lbl_status.setText("")

    def apply_preset(self, val):
        self.syncing = True
        for s in ["top", "bottom", "left", "right"]:
            self.spins[s].setValue(val)
        self.syncing = False
        self.preview.update_gaps(val, val, val, val)
        self.lbl_status.setText("")

    def reset_defaults(self):
        self.apply_preset(15)
        self.chk_sync.setChecked(True)
        self.chk_compensate_dock.setChecked(True)
        self.spin_dock_margin.setValue(12)
        self.chk_auto_maximize.setChecked(False)
        self.chk_fullscreen.setChecked(False)
        self.edit_ignored.setText("")
        self.lbl_status.setText("Reset to defaults (click Apply to save)")

    def save_and_apply(self):
        t = self.spins["top"].value()
        b = self.spins["bottom"].value()
        l = self.spins["left"].value()
        r = self.spins["right"].value()

        write_kwin_config("gapTop", t)
        write_kwin_config("gapBottom", b)
        write_kwin_config("gapLeft", l)
        write_kwin_config("gapRight", r)

        write_kwin_config("compensateDock", self.chk_compensate_dock.isChecked())
        write_kwin_config("dockMargin", self.spin_dock_margin.value())
        write_kwin_config("autoMaximizeNewWindows", self.chk_auto_maximize.isChecked())
        write_kwin_config("applyToFullscreen", self.chk_fullscreen.isChecked())
        write_kwin_config("ignoredApps", self.edit_ignored.text().strip())

        # Trigger KWin reconfigure
        reconfigure_kwin()
        self.lbl_status.setText("✓ Settings saved & applied!")


def main():
    app = QApplication(sys.argv)
    window = SettingsWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
