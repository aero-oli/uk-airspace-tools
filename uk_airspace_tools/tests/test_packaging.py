import configparser
import unittest
from pathlib import Path
from zipfile import ZipFile


REPO_ROOT = Path(__file__).resolve().parents[2]
PLUGIN_DIR = REPO_ROOT / "uk_airspace_tools"
ZIP_PATH = REPO_ROOT / "dist" / "uk_airspace_tools.zip"


class PackagingTest(unittest.TestCase):
    def test_metadata_icon_exists_and_is_referenced_by_qrc(self):
        metadata = configparser.ConfigParser()
        metadata.read(PLUGIN_DIR / "metadata.txt", encoding="utf-8")
        icon = metadata["general"].get("icon")

        self.assertEqual(icon, "icon.svg")
        self.assertTrue((PLUGIN_DIR / icon).is_file())
        self.assertIn("<file>icon.svg</file>", (PLUGIN_DIR / "resources.qrc").read_text(encoding="utf-8"))

    def test_metadata_keeps_operational_warning(self):
        about = (PLUGIN_DIR / "metadata.txt").read_text(encoding="utf-8").lower()

        self.assertIn("not a replacement for official briefing", about)
        self.assertIn("operational flight planning", about)

    def test_built_plugin_zip_contains_plugin_root_and_icon(self):
        if not ZIP_PATH.exists():
            self.skipTest("Build dist/uk_airspace_tools.zip before running zip-content checks.")

        with ZipFile(ZIP_PATH) as archive:
            names = set(archive.namelist())

        self.assertIn("uk_airspace_tools/metadata.txt", names)
        self.assertIn("uk_airspace_tools/icon.svg", names)
        self.assertIn("uk_airspace_tools/plugin.py", names)

    def test_built_plugin_zip_excludes_runtime_caches(self):
        if not ZIP_PATH.exists():
            self.skipTest("Build dist/uk_airspace_tools.zip before running zip-content checks.")

        with ZipFile(ZIP_PATH) as archive:
            names = set(archive.namelist())

        forbidden_suffixes = (".pyc", ".pyo", ".gpkg")
        self.assertFalse(any(name.endswith(forbidden_suffixes) for name in names))
        self.assertFalse(any("__pycache__/" in name for name in names))


if __name__ == "__main__":
    unittest.main()
