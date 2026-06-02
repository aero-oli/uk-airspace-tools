import unittest

from uk_airspace_tools.geometry.coordinate_parser import parse_compact_coordinate
from uk_airspace_tools.parsers.q_line import parse_q_line
from uk_airspace_tools.tests.sample_notams import SAMPLE_Q_LINE


class QLineParserTest(unittest.TestCase):
    def test_coordinate_parser(self):
        lat, lon = parse_compact_coordinate("5120N00030W")
        self.assertAlmostEqual(lat, 51.333333, places=5)
        self.assertAlmostEqual(lon, -0.5, places=5)

    def test_q_line_radius_and_flight_levels(self):
        parsed = parse_q_line(SAMPLE_Q_LINE)
        self.assertEqual(parsed.fir, "EGTT")
        self.assertEqual(parsed.qcode, "QWELW")
        self.assertEqual(parsed.traffic, "IV")
        self.assertEqual(parsed.purpose, "BO")
        self.assertEqual(parsed.lower_fl, 0)
        self.assertEqual(parsed.upper_fl, 20)
        self.assertEqual(parsed.radius_nm, 5)
        self.assertAlmostEqual(parsed.latitude, 51.333333, places=5)
        self.assertAlmostEqual(parsed.longitude, -0.5, places=5)


if __name__ == "__main__":
    unittest.main()

