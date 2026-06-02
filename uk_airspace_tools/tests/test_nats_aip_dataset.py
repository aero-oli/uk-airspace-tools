import unittest

from uk_airspace_tools.providers.nats_aip_dataset import NatsAipDatasetProvider


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


if __name__ == "__main__":
    unittest.main()
