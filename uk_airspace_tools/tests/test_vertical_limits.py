import unittest

from uk_airspace_tools.parsers.vertical_limits import parse_vertical_limit


class VerticalLimitParserTest(unittest.TestCase):
    def test_surface_values(self):
        self.assertEqual(parse_vertical_limit("SFC").reference, "SFC")
        self.assertEqual(parse_vertical_limit("GND").reference, "GND")

    def test_unlimited(self):
        parsed = parse_vertical_limit("UNL")
        self.assertEqual(parsed.unit, "UNL")
        self.assertIsNone(parsed.value)

    def test_flight_level_values(self):
        self.assertEqual(parse_vertical_limit("FL020").value, 20)
        self.assertEqual(parse_vertical_limit("020").unit, "FL")

    def test_feet_values(self):
        parsed = parse_vertical_limit("1000FT AMSL")
        self.assertEqual(parsed.value, 1000)
        self.assertEqual(parsed.unit, "FT")
        self.assertEqual(parsed.reference, "AMSL")

        parsed = parse_vertical_limit("1500FT AGL")
        self.assertEqual(parsed.reference, "AGL")


if __name__ == "__main__":
    unittest.main()

