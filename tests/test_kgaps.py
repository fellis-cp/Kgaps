"""Unit tests for KGaps metadata, configuration schema, settings backend, and UI."""

import json
import os
import subprocess
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest import mock

import kgaps_settings

ROOT_DIR = Path(__file__).resolve().parent.parent


class TestMetadataAndSchema(unittest.TestCase):
    """Verify metadata.json, main.xml, config.ui, main.js, and kgaps_settings.py stay in sync."""

    def test_metadata_json_valid(self):
        meta_path = ROOT_DIR / "metadata.json"
        data = json.loads(meta_path.read_text(encoding="utf-8"))
        self.assertEqual(data.get("KPackageStructure"), "KWin/Script")
        plugin = data.get("KPlugin", {})
        self.assertEqual(plugin.get("Id"), "kgaps")
        self.assertEqual(plugin.get("Version"), kgaps_settings.APP_VERSION)
        self.assertTrue(plugin.get("Name"))
        self.assertTrue(plugin.get("Description"))

    def test_kcfg_and_ui_keys_match(self):
        main_xml = ROOT_DIR / "contents" / "config" / "main.xml"
        config_ui = ROOT_DIR / "contents" / "ui" / "config.ui"

        kcfg_root = ET.parse(main_xml).getroot()
        ns = {"kcfg": "http://www.kde.org/standards/kcfg/1.0"}
        kcfg_keys = {
            entry.attrib["name"]
            for entry in kcfg_root.findall(".//kcfg:entry", ns)
        }
        self.assertEqual(kcfg_keys, set(kgaps_settings.DEFAULT_CONFIG.keys()))

        ui_root = ET.parse(config_ui).getroot()
        ui_kcfg_widgets = {
            widget.attrib["name"].removeprefix("kcfg_")
            for widget in ui_root.findall(".//widget")
            if widget.attrib.get("name", "").startswith("kcfg_")
        }
        self.assertEqual(kcfg_keys, ui_kcfg_widgets)

    def test_main_js_reads_all_config_keys(self):
        main_js = (ROOT_DIR / "contents" / "code" / "main.js").read_text(encoding="utf-8")
        for key in kgaps_settings.DEFAULT_CONFIG:
            self.assertIn(f'readConfig("{key}"', main_js)


class TestConfigReadWrite(unittest.TestCase):
    """Test kwinrc config reading, writing, and fallback INI handling."""

    def test_fallback_write_and_read_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with mock.patch.dict(os.environ, {"XDG_CONFIG_HOME": tmpdir}):
                with mock.patch("shutil.which", return_value=None):
                    self.assertTrue(kgaps_settings.write_kwin_config("gapTop", 24))
                    self.assertTrue(kgaps_settings.write_kwin_config("compensateDock", False))
                    self.assertTrue(kgaps_settings.write_kwin_config("ignoredApps", "vlc, steam"))

                    self.assertEqual(kgaps_settings.read_kwin_config("gapTop", 15), 24)
                    self.assertFalse(kgaps_settings.read_kwin_config("compensateDock", True))
                    self.assertEqual(kgaps_settings.read_kwin_config("ignoredApps", ""), "vlc, steam")
                    self.assertEqual(kgaps_settings.read_kwin_config("missingKey", 99), 99)

    def test_kreadconfig6_subprocess_path(self):
        fake_res = mock.Mock(returncode=0, stdout="42\n")
        with mock.patch("shutil.which", return_value="/usr/bin/kreadconfig6"):
            with mock.patch("subprocess.run", return_value=fake_res) as run_mock:
                val = kgaps_settings.read_kwin_config("gapLeft", 15)
                self.assertEqual(val, 42)
                run_mock.assert_called_once()

    def test_reconfigure_kwin_uses_qdbus(self):
        fake_res = mock.Mock(returncode=0)
        with mock.patch("shutil.which", side_effect=lambda name: "/usr/bin/qdbus" if name == "qdbus" else None):
            with mock.patch("subprocess.run", return_value=fake_res) as run_mock:
                self.assertTrue(kgaps_settings.reconfigure_kwin())
                self.assertEqual(run_mock.call_count, 2)

    def test_reconfigure_kwin_returns_false_when_no_dbus(self):
        with mock.patch("shutil.which", return_value=None):
            self.assertFalse(kgaps_settings.reconfigure_kwin())


class TestShellScriptsSyntax(unittest.TestCase):
    """Ensure all shell scripts pass bash -n syntax check."""

    def test_bash_syntax(self):
        for script in ("install.sh", "uninstall.sh", "reload.sh", "settings.sh"):
            res = subprocess.run(["bash", "-n", str(ROOT_DIR / script)], capture_output=True, text=True, check=False)
            self.assertEqual(res.returncode, 0, msg=f"{script}: {res.stderr}")


@unittest.skipIf(kgaps_settings.QtWidgets is None, "Qt6 Python bindings not installed")
class TestSettingsGUI(unittest.TestCase):
    """Smoke tests for the Qt6 SettingsWindow in offscreen mode."""

    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        cls.app = kgaps_settings.QApplication.instance() or kgaps_settings.QApplication([])

    def test_window_load_preset_and_reset(self):
        with mock.patch.object(kgaps_settings, "read_kwin_config", side_effect=lambda k, d: d):
            win = kgaps_settings.SettingsWindow()
            self.assertEqual(win.spins["top"].value(), 15)
            win.apply_preset(30)
            for side in ("top", "bottom", "left", "right"):
                self.assertEqual(win.spins[side].value(), 30)
            win.reset_defaults()
            self.assertEqual(win.spins["top"].value(), 15)
            win.close()

    def test_window_quick_tile_controls(self):
        with mock.patch.object(kgaps_settings, "read_kwin_config", side_effect=lambda k, d: d):
            win = kgaps_settings.SettingsWindow()
            self.assertTrue(win.chk_quick_tile.isChecked())
            self.assertEqual(win.spin_inner_gap.value(), 10)
            win.chk_quick_tile.setChecked(False)
            self.assertFalse(win.spin_inner_gap.isEnabled())
            win.reset_defaults()
            self.assertTrue(win.chk_quick_tile.isChecked())
            self.assertEqual(win.spin_inner_gap.value(), 10)
            self.assertTrue(win.spin_inner_gap.isEnabled())
            win.close()


if __name__ == "__main__":
    unittest.main()
