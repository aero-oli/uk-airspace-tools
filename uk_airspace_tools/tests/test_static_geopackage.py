import unittest

from uk_airspace_tools.providers.nats_aip_dataset import PermanentAirspaceFeature
from uk_airspace_tools.storage.static_geopackage import StaticAirspaceCache


def _feature(category="Controlled airspace", geometry_wkt="POLYGON ((0 0, 1 0, 1 1, 0 0))"):
    return PermanentAirspaceFeature(
        id="TEST",
        name="Test airspace",
        designator="TEST",
        airspace_type="CTA",
        local_type=None,
        category=category,
        airspace_class=None,
        lower_limit_raw=None,
        upper_limit_raw=None,
        lower_limit_value=None,
        upper_limit_value=None,
        lower_limit_unit=None,
        upper_limit_unit=None,
        lower_limit_reference=None,
        upper_limit_reference=None,
        lower_altitude_ft=None,
        upper_altitude_ft=None,
        activation_status=None,
        effective_start=None,
        effective_end=None,
        source="test",
        source_file=None,
        source_effective_date=None,
        remarks=None,
        geometry_quality="test",
        geometry_wkt=geometry_wkt,
        raw_properties=None,
    )


class StaticGeoPackageRoutingTest(unittest.TestCase):
    def test_geometry_feature_routes_by_category(self):
        self.assertEqual(StaticAirspaceCache._target_layer_key(_feature()), "controlled")

    def test_geometryless_feature_routes_to_text_only_layer(self):
        self.assertEqual(StaticAirspaceCache._target_layer_key(_feature(geometry_wkt=None)), "text_only")

    def test_unknown_category_routes_to_other(self):
        self.assertEqual(StaticAirspaceCache._target_layer_key(_feature(category="Unexpected")), "other")


if __name__ == "__main__":
    unittest.main()
