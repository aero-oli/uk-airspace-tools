from datetime import datetime, timezone
import unittest

from uk_airspace_tools.parsers.notam import parse_notam_block, parse_notams_from_xml
from uk_airspace_tools.tests.sample_notams import MALFORMED_NOTAM, SAMPLE_NOTAM, STRUCTURED_PIB_XML, TEXT_ONLY_NOTAM


class NotamParserTest(unittest.TestCase):
    def test_basic_notam_block_parsing(self):
        feature = parse_notam_block(SAMPLE_NOTAM, source="test")
        self.assertEqual(feature.id, "A1234/24")
        self.assertEqual(feature.fir, "EGTT")
        self.assertEqual(feature.icao_location, "EGTT")
        self.assertEqual(feature.qcode, "QWELW")
        self.assertEqual(feature.geometry_quality, "qline_radius")
        self.assertTrue(feature.geometry_wkt.startswith("POLYGON"))
        self.assertEqual(feature.lower_limit_reference, "SFC")
        self.assertEqual(feature.upper_limit_unit, "FT")
        self.assertEqual(feature.upper_limit_reference, "AMSL")

    def test_missing_geometry_becomes_text_only(self):
        feature = parse_notam_block(TEXT_ONLY_NOTAM, source="test")
        self.assertEqual(feature.geometry_quality, "text_only")
        self.assertIsNone(feature.geometry_wkt)
        self.assertGreaterEqual(len(feature.parse_warnings), 1)

    def test_malformed_notam_does_not_crash(self):
        feature = parse_notam_block(MALFORMED_NOTAM, source="test")
        self.assertTrue(feature.id.startswith("NOTAM-"))
        self.assertEqual(feature.raw_text, MALFORMED_NOTAM)
        self.assertEqual(feature.geometry_quality, "text_only")
        self.assertGreaterEqual(len(feature.parse_warnings), 1)

    def test_structured_pib_notam_parsing(self):
        features = parse_notams_from_xml(STRUCTURED_PIB_XML.encode("utf-8"), source="test")

        self.assertEqual(len(features), 1)
        feature = features[0]
        self.assertEqual(feature.id, "L2624/26")
        self.assertEqual(feature.icao_location, "EGNL")
        self.assertEqual(feature.fir, "EGTT")
        self.assertEqual(feature.qcode, "QILXX")
        self.assertEqual(feature.activity_group, "Navigation and procedures")
        self.assertEqual(feature.radius_nm, 5)
        self.assertEqual(feature.lower_altitude_ft, 0)
        self.assertEqual(feature.upper_altitude_ft, 99900)
        self.assertEqual(feature.geometry_quality, "qline_radius")
        self.assertTrue(feature.geometry_wkt.startswith("POLYGON"))
        self.assertEqual(feature.effective_start, datetime(2026, 5, 1, 8, 15, tzinfo=timezone.utc))
        self.assertEqual(feature.effective_end, datetime(2026, 6, 30, 23, 59, tzinfo=timezone.utc))
        self.assertEqual(feature.parse_warnings, [])


if __name__ == "__main__":
    unittest.main()
