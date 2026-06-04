from datetime import datetime, timezone
import unittest

from uk_airspace_tools.qgis_layers.layer_manager import LayerManager


class FakeLayer:
    def __init__(self, name="Fake layer", fail_subset=False):
        self._name = name
        self.fail_subset = fail_subset
        self.subset = None
        self.extents_updated = False
        self.repainted = False

    def name(self):
        return self._name

    def setSubsetString(self, subset):
        if self.fail_subset:
            raise RuntimeError("bad subset")
        self.subset = subset

    def updateExtents(self):
        self.extents_updated = True

    def triggerRepaint(self):
        self.repainted = True


class LayerFilterTest(unittest.TestCase):
    def test_today_filter_uses_whole_utc_day(self):
        expression = LayerManager._subset_expression(
            time_filter="today",
            custom_start_date="",
            custom_end_date="",
            status_filter="all",
            activity_filter="all",
            fir_filter="all",
            scope_filter="all",
            qcode_filter="all",
            radius_filter="all",
            altitude_filter="all",
            custom_min_altitude_ft="",
            custom_max_altitude_ft="",
            keyword="",
            show_expired=True,
        )

        self.assertIn("effective_start IS NULL OR effective_start <", expression)
        self.assertIn("effective_end IS NULL OR effective_end >=", expression)

    def test_custom_date_filter_builds_overlap_expression(self):
        now = datetime(2026, 6, 2, 12, 0, tzinfo=timezone.utc)
        start, end = LayerManager._date_window("custom_dates", "2026-06-10", "2026-06-12", now)

        self.assertEqual(start, datetime(2026, 6, 10, 0, 0, tzinfo=timezone.utc))
        self.assertEqual(end, datetime(2026, 6, 13, 0, 0, tzinfo=timezone.utc))

    def test_custom_date_filter_accepts_swapped_dates(self):
        now = datetime(2026, 6, 2, 12, 0, tzinfo=timezone.utc)
        start, end = LayerManager._date_window("custom_dates", "2026-06-12", "2026-06-10", now)

        self.assertEqual(start, datetime(2026, 6, 10, 0, 0, tzinfo=timezone.utc))
        self.assertEqual(end, datetime(2026, 6, 13, 0, 0, tzinfo=timezone.utc))

    def test_static_filter_combines_category_type_altitude_and_keyword(self):
        expression = LayerManager._static_subset_expression(
            static_category_filter="Controlled airspace",
            static_type_filter="CTA",
            altitude_filter="sfc_fl100",
            custom_min_altitude_ft="",
            custom_max_altitude_ft="",
            keyword="Moray",
        )

        self.assertIn("category = 'Controlled airspace'", expression)
        self.assertIn("airspace_type = 'CTA'", expression)
        self.assertIn("lower_altitude_ft", expression)
        self.assertIn("name LIKE '%Moray%'", expression)

    def test_notam_keyword_filter_searches_operational_fields(self):
        expression = LayerManager._subset_expression(
            time_filter="all",
            custom_start_date="",
            custom_end_date="",
            status_filter="all",
            activity_filter="all",
            fir_filter="all",
            scope_filter="all",
            qcode_filter="all",
            radius_filter="all",
            altitude_filter="all",
            custom_min_altitude_ft="",
            custom_max_altitude_ft="",
            keyword="EGTT",
            show_expired=True,
        )

        self.assertIn("id LIKE '%EGTT%'", expression)
        self.assertIn("qcode LIKE '%EGTT%'", expression)
        self.assertIn("icao_location LIKE '%EGTT%'", expression)
        self.assertIn("raw_text LIKE '%EGTT%'", expression)

    def test_static_keyword_filter_searches_airspace_identity_fields(self):
        expression = LayerManager._static_subset_expression(
            static_category_filter="all",
            static_type_filter="all",
            altitude_filter="all",
            custom_min_altitude_ft="",
            custom_max_altitude_ft="",
            keyword="CTA",
        )

        self.assertIn("id LIKE '%CTA%'", expression)
        self.assertIn("airspace_type LIKE '%CTA%'", expression)
        self.assertIn("category LIKE '%CTA%'", expression)
        self.assertIn("remarks LIKE '%CTA%'", expression)

    def test_keyword_filter_escapes_single_quotes(self):
        expression = LayerManager._subset_expression(
            time_filter="all",
            custom_start_date="",
            custom_end_date="",
            status_filter="all",
            activity_filter="all",
            fir_filter="all",
            scope_filter="all",
            qcode_filter="all",
            radius_filter="all",
            altitude_filter="all",
            custom_min_altitude_ft="",
            custom_max_altitude_ft="",
            keyword="O'Hare",
            show_expired=True,
        )

        self.assertIn("O''Hare", expression)

    def test_apply_subset_updates_layer_when_subset_is_valid(self):
        layer = FakeLayer()
        manager = LayerManager(iface=None)

        manager._apply_subset(layer, "id = 'A1234/26'", "NOTAM")

        self.assertEqual(layer.subset, "id = 'A1234/26'")
        self.assertTrue(layer.extents_updated)
        self.assertTrue(layer.repainted)

    def test_apply_subset_reports_layer_name_and_expression_when_subset_fails(self):
        warnings = []
        layer = FakeLayer(name="NOTAM polygons", fail_subset=True)
        manager = LayerManager(iface=None, warning_handler=warnings.append)

        manager._apply_subset(layer, "bad expression", "NOTAM")

        self.assertEqual(len(warnings), 1)
        self.assertIn("NOTAM polygons", warnings[0])
        self.assertIn("bad expression", warnings[0])
        self.assertIn("bad subset", warnings[0])


if __name__ == "__main__":
    unittest.main()
