from datetime import datetime, timezone
import unittest

from uk_airspace_tools.qgis_layers.layer_manager import LayerManager


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


if __name__ == "__main__":
    unittest.main()
