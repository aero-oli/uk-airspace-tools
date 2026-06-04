import unittest
from types import SimpleNamespace

from uk_airspace_tools.plugin import UkAirspaceToolsPlugin


class PluginDiagnosticsTest(unittest.TestCase):
    def test_warning_records_preserve_feature_identity_and_category(self):
        features = [
            SimpleNamespace(id="A1234/26", activity_group="Aerial activity", parse_warnings=["Missing schedule."]),
            SimpleNamespace(id="EGCTA", category="Controlled airspace", parse_warnings=["Unsupported segment."]),
            SimpleNamespace(id="CLEAN", activity_group="Other", parse_warnings=[]),
        ]

        records = UkAirspaceToolsPlugin._warning_records("notam", features)

        self.assertEqual(
            records,
            [
                {
                    "kind": "notam",
                    "feature_id": "A1234/26",
                    "category": "Aerial activity",
                    "warning": "Missing schedule.",
                },
                {
                    "kind": "notam",
                    "feature_id": "EGCTA",
                    "category": "Controlled airspace",
                    "warning": "Unsupported segment.",
                },
            ],
        )

    def test_static_airspace_inspection_state_uses_polygon_count_when_available(self):
        layers = {"controlled": object(), "text_only": object()}

        self.assertTrue(UkAirspaceToolsPlugin._has_inspectable_static_airspace(layers, {"permanent_polygon_count": 1}))
        self.assertFalse(UkAirspaceToolsPlugin._has_inspectable_static_airspace(layers, {"permanent_polygon_count": 0}))
        self.assertTrue(UkAirspaceToolsPlugin._has_inspectable_static_airspace(layers, {}))

    def test_show_parse_warnings_writes_review_to_dock_details(self):
        class FakeDock:
            def set_feature_details(self, title, details, rich=False):
                self.title = title
                self.details = details
                self.rich = rich

        dock = FakeDock()
        plugin = object.__new__(UkAirspaceToolsPlugin)
        plugin.dock = dock
        plugin.latest_parse_warnings = [
            {
                "kind": "notam",
                "feature_id": "A1234/26",
                "category": "Aerial activity",
                "warning": "Missing geometry <circle>.",
            }
        ]

        plugin.show_parse_warnings()

        self.assertEqual(dock.title, "Parse warnings")
        self.assertTrue(dock.rich)
        self.assertIn("A1234/26", dock.details)
        self.assertIn("Aerial activity", dock.details)
        self.assertIn("Missing geometry &lt;circle&gt;.", dock.details)

    def test_show_parse_warnings_handles_empty_warning_list(self):
        class FakeDock:
            def set_feature_details(self, title, details, rich=False):
                self.title = title
                self.details = details
                self.rich = rich

        dock = FakeDock()
        plugin = object.__new__(UkAirspaceToolsPlugin)
        plugin.dock = dock
        plugin.latest_parse_warnings = []

        plugin.show_parse_warnings()

        self.assertEqual(dock.title, "Parse warnings")
        self.assertFalse(dock.rich)
        self.assertIn("No parse warnings", dock.details)


if __name__ == "__main__":
    unittest.main()
