import unittest
import xml.etree.ElementTree as ET

from uk_airspace_tools.providers.nats_aip_dataset import NatsAipDatasetProvider, _radius_nm, _segment_points, _volume_geometry_wkt


SAMPLE_AIXM = """<?xml version="1.0" encoding="UTF-8"?>
<message:AIXMBasicMessage
  xmlns:aixm="http://www.aixm.aero/schema/5.1"
  xmlns:gml="http://www.opengis.net/gml/3.2"
  xmlns:message="http://www.aixm.aero/schema/5.1/message">
  <message:hasMember>
    <aixm:Airspace>
      <gml:identifier codeSpace="urn:uuid:">sample-airspace</gml:identifier>
      <aixm:timeSlice>
        <aixm:AirspaceTimeSlice gml:id="ts1">
          <gml:validTime>
            <gml:TimePeriod gml:id="tp1">
              <gml:beginPosition>2026-05-14T00:00:00Z</gml:beginPosition>
              <gml:endPosition indeterminatePosition="unknown"/>
            </gml:TimePeriod>
          </gml:validTime>
          <aixm:type>CTA</aixm:type>
          <aixm:designator>EGSAMPLE001</aixm:designator>
          <aixm:name>SAMPLE CTA</aixm:name>
          <aixm:class>
            <aixm:AirspaceLayerClass gml:id="class1">
              <aixm:classification>D</aixm:classification>
            </aixm:AirspaceLayerClass>
          </aixm:class>
          <aixm:geometryComponent>
            <aixm:AirspaceGeometryComponent gml:id="gc1">
              <aixm:theAirspaceVolume>
                <aixm:AirspaceVolume gml:id="vol1">
                  <aixm:upperLimit uom="FL">105</aixm:upperLimit>
                  <aixm:upperLimitReference>STD</aixm:upperLimitReference>
                  <aixm:lowerLimit uom="FT">1500</aixm:lowerLimit>
                  <aixm:lowerLimitReference>MSL</aixm:lowerLimitReference>
                  <aixm:horizontalProjection>
                    <aixm:Surface srsName="urn:ogc:def:crs:EPSG::4326" gml:id="surface1">
                      <gml:patches>
                        <gml:PolygonPatch>
                          <gml:exterior>
                            <gml:Ring>
                              <gml:curveMember>
                                <gml:Curve gml:id="curve1">
                                  <gml:segments>
                                    <gml:GeodesicString>
                                      <gml:pointProperty><gml:Point><gml:pos>51.0 -1.0</gml:pos></gml:Point></gml:pointProperty>
                                      <gml:pointProperty><gml:Point><gml:pos>51.0 -1.1</gml:pos></gml:Point></gml:pointProperty>
                                      <gml:pointProperty><gml:Point><gml:pos>51.1 -1.1</gml:pos></gml:Point></gml:pointProperty>
                                      <gml:pointProperty><gml:Point><gml:pos>51.0 -1.0</gml:pos></gml:Point></gml:pointProperty>
                                    </gml:GeodesicString>
                                  </gml:segments>
                                </gml:Curve>
                              </gml:curveMember>
                            </gml:Ring>
                          </gml:exterior>
                        </gml:PolygonPatch>
                      </gml:patches>
                    </aixm:Surface>
                  </aixm:horizontalProjection>
                </aixm:AirspaceVolume>
              </aixm:theAirspaceVolume>
            </aixm:AirspaceGeometryComponent>
          </aixm:geometryComponent>
          <aixm:annotation>
            <aixm:Note gml:id="note1">
              <aixm:translatedNote>
                <aixm:LinguisticNote><aixm:note>Sample remark.</aixm:note></aixm:LinguisticNote>
              </aixm:translatedNote>
            </aixm:Note>
          </aixm:annotation>
        </aixm:AirspaceTimeSlice>
      </aixm:timeSlice>
    </aixm:Airspace>
  </message:hasMember>
</message:AIXMBasicMessage>
"""


class NatsAipDatasetProviderTest(unittest.TestCase):
    def test_parse_aixm_airspace(self):
        provider = NatsAipDatasetProvider()
        features = provider.parse(SAMPLE_AIXM.encode("utf-8"))

        self.assertEqual(len(features), 1)
        feature = features[0]
        self.assertEqual(feature.id, "EGSAMPLE001")
        self.assertEqual(feature.category, "Controlled airspace")
        self.assertEqual(feature.airspace_type, "CTA")
        self.assertEqual(feature.airspace_class, "D")
        self.assertEqual(feature.lower_altitude_ft, 1500)
        self.assertEqual(feature.upper_altitude_ft, 10500)
        self.assertTrue(feature.geometry_wkt.startswith("POLYGON"))
        self.assertEqual(feature.parse_warnings, [])

    def test_segment_points_supports_pos_list(self):
        segment = ET.fromstring(
            """
            <gml:GeodesicString xmlns:gml="http://www.opengis.net/gml/3.2">
              <gml:posList>51.0 -1.0 51.1 -1.1 51.2 -1.2</gml:posList>
            </gml:GeodesicString>
            """
        )

        self.assertEqual(_segment_points(segment), [(51.0, -1.0), (51.1, -1.1), (51.2, -1.2)])

    def test_radius_units_convert_to_nautical_miles(self):
        metres = ET.fromstring('<gml:CircleByCenterPoint xmlns:gml="http://www.opengis.net/gml/3.2"><gml:radius uom="M">1852</gml:radius></gml:CircleByCenterPoint>')
        kilometres = ET.fromstring('<gml:CircleByCenterPoint xmlns:gml="http://www.opengis.net/gml/3.2"><gml:radius uom="KM">1.852</gml:radius></gml:CircleByCenterPoint>')
        feet = ET.fromstring('<gml:CircleByCenterPoint xmlns:gml="http://www.opengis.net/gml/3.2"><gml:radius uom="FT">6076.12</gml:radius></gml:CircleByCenterPoint>')

        self.assertAlmostEqual(_radius_nm(metres), 1.0)
        self.assertAlmostEqual(_radius_nm(kilometres), 1.0)
        self.assertAlmostEqual(_radius_nm(feet), 1.0)

    def test_volume_geometry_preserves_interior_rings(self):
        volume = ET.fromstring(
            """
            <aixm:AirspaceVolume xmlns:aixm="http://www.aixm.aero/schema/5.1" xmlns:gml="http://www.opengis.net/gml/3.2">
              <aixm:horizontalProjection>
                <aixm:Surface>
                  <gml:patches>
                    <gml:PolygonPatch>
                      <gml:exterior><gml:Ring><gml:curveMember><gml:Curve><gml:segments>
                        <gml:GeodesicString><gml:posList>51.0 -1.0 51.0 -1.2 51.2 -1.2 51.2 -1.0 51.0 -1.0</gml:posList></gml:GeodesicString>
                      </gml:segments></gml:Curve></gml:curveMember></gml:Ring></gml:exterior>
                      <gml:interior><gml:Ring><gml:curveMember><gml:Curve><gml:segments>
                        <gml:GeodesicString><gml:posList>51.05 -1.05 51.05 -1.10 51.10 -1.10 51.10 -1.05 51.05 -1.05</gml:posList></gml:GeodesicString>
                      </gml:segments></gml:Curve></gml:curveMember></gml:Ring></gml:interior>
                    </gml:PolygonPatch>
                  </gml:patches>
                </aixm:Surface>
              </aixm:horizontalProjection>
            </aixm:AirspaceVolume>
            """
        )

        wkt, quality, warnings = _volume_geometry_wkt(volume)

        self.assertEqual(quality, "aixm_polygon")
        self.assertTrue(wkt.startswith("POLYGON"))
        self.assertIn("), (", wkt)
        self.assertEqual(warnings, [])

    def test_volume_geometry_uses_multipolygon_for_multiple_surfaces(self):
        volume = ET.fromstring(
            """
            <aixm:AirspaceVolume xmlns:aixm="http://www.aixm.aero/schema/5.1" xmlns:gml="http://www.opengis.net/gml/3.2">
              <aixm:horizontalProjection>
                <aixm:Surface>
                  <gml:patches><gml:PolygonPatch><gml:exterior><gml:Ring><gml:curveMember><gml:Curve><gml:segments>
                    <gml:GeodesicString><gml:posList>51.0 -1.0 51.0 -1.1 51.1 -1.1 51.0 -1.0</gml:posList></gml:GeodesicString>
                  </gml:segments></gml:Curve></gml:curveMember></gml:Ring></gml:exterior></gml:PolygonPatch></gml:patches>
                </aixm:Surface>
                <aixm:Surface>
                  <gml:patches><gml:PolygonPatch><gml:exterior><gml:Ring><gml:curveMember><gml:Curve><gml:segments>
                    <gml:GeodesicString><gml:posList>52.0 -2.0 52.0 -2.1 52.1 -2.1 52.0 -2.0</gml:posList></gml:GeodesicString>
                  </gml:segments></gml:Curve></gml:curveMember></gml:Ring></gml:exterior></gml:PolygonPatch></gml:patches>
                </aixm:Surface>
              </aixm:horizontalProjection>
            </aixm:AirspaceVolume>
            """
        )

        wkt, quality, warnings = _volume_geometry_wkt(volume)

        self.assertEqual(quality, "aixm_multipolygon")
        self.assertTrue(wkt.startswith("MULTIPOLYGON"))
        self.assertEqual(warnings, [])

    def test_volume_geometry_reports_unsupported_segments(self):
        volume = ET.fromstring(
            """
            <aixm:AirspaceVolume xmlns:aixm="http://www.aixm.aero/schema/5.1" xmlns:gml="http://www.opengis.net/gml/3.2">
              <aixm:horizontalProjection>
                <aixm:Surface>
                  <gml:patches><gml:PolygonPatch><gml:exterior><gml:Ring><gml:curveMember><gml:Curve><gml:segments>
                    <gml:Clothoid/>
                  </gml:segments></gml:Curve></gml:curveMember></gml:Ring></gml:exterior></gml:PolygonPatch></gml:patches>
                </aixm:Surface>
              </aixm:horizontalProjection>
            </aixm:AirspaceVolume>
            """
        )

        wkt, quality, warnings = _volume_geometry_wkt(volume)

        self.assertIsNone(wkt)
        self.assertEqual(quality, "text_only")
        self.assertIn("Unsupported AIXM geometry segment 'Clothoid' was skipped.", warnings)


if __name__ == "__main__":
    unittest.main()
