import unittest
from datetime import date

from uk_airspace_tools.providers.nats_aip_dataset import NatsAipDatasetProvider
from uk_airspace_tools.providers.nats_pib_xml import NatsPibXmlProvider


class FakePibProvider(NatsPibXmlProvider):
    def __init__(self, responses):
        super().__init__("https://example.test/pib-page")
        self.responses = responses

    def _download(self, url: str):
        response = self.responses[url]
        if isinstance(response, Exception):
            raise response
        return response


class FakeAipProvider(NatsAipDatasetProvider):
    def __init__(self, page_html: str, today: date):
        super().__init__(today=today)
        self.page_html = page_html

    def _download(self, url: str) -> bytes:
        return self.page_html.encode("utf-8")


class NatsPibXmlProviderTest(unittest.TestCase):
    def test_fetch_returns_direct_xml_response(self):
        provider = FakePibProvider(
            {
                "https://example.test/pib-page": (
                    b"<?xml version='1.0'?><NOTAMSet/>",
                    "application/xml",
                    "https://example.test/PIB.xml",
                )
            }
        )

        raw = provider.fetch()

        self.assertEqual(raw, b"<?xml version='1.0'?><NOTAMSet/>")
        self.assertEqual(provider.resolved_url, "https://example.test/PIB.xml")
        self.assertEqual(provider.content_type, "application/xml")

    def test_fetch_discovers_ranked_xml_candidate_from_html_page(self):
        provider = FakePibProvider(
            {
                "https://example.test/pib-page": (
                    b"<html><a href='/files/readme.txt'>Readme</a><a href='/files/current-notam-pib.xml'>PIB</a></html>",
                    "text/html",
                    "https://example.test/pib-page",
                ),
                "https://example.test/files/current-notam-pib.xml": (
                    b"<notam>A1234/26 Q) EGTT/QWALW/IV/M/AW/000/050/5120N00030W005</notam>",
                    "application/xml",
                    "https://example.test/files/current-notam-pib.xml",
                ),
            }
        )

        raw = provider.fetch()

        self.assertIn(b"A1234/26", raw)
        self.assertEqual(provider.resolved_url, "https://example.test/files/current-notam-pib.xml")

    def test_fetch_reports_candidate_errors_when_no_xml_can_be_downloaded(self):
        provider = FakePibProvider(
            {
                "https://example.test/pib-page": (
                    b"<html><a href='/pib.xml'>PIB</a></html>",
                    "text/html",
                    "https://example.test/pib-page",
                ),
                "https://example.test/pib.xml": RuntimeError("offline"),
            }
        )

        with self.assertRaisesRegex(RuntimeError, "offline"):
            provider.fetch()

    def test_find_xml_candidates_deduplicates_and_ranks_links(self):
        html = """
        <a href="/briefing.txt">briefing</a>
        <a href="/old.xml">old</a>
        <a href="/notam-pib.xml">current</a>
        <a href="/notam-pib.xml">duplicate</a>
        """

        candidates = NatsPibXmlProvider._find_xml_candidates(html, "https://example.test/base/")

        self.assertEqual(candidates[0], "https://example.test/notam-pib.xml")
        self.assertEqual(candidates.count("https://example.test/notam-pib.xml"), 1)


class NatsAipDatasetProviderDiscoveryTest(unittest.TestCase):
    def test_discover_current_dataset_chooses_latest_effective_xml_not_after_today(self):
        html = """
        <a href="ICAO_AIP/EG_AIP_DS_20260514_XML.zip">May XML</a>
        <a href="ICAO_AIP/EG_AIP_DS_FULL_20260514_KML.zip">May KML</a>
        <a href="ICAO_AIP/EG_AIP_DS_20260612_XML.zip">June XML</a>
        <a href="ICAO_AIP/EG_AIP_DS_FULL_20260612_KML.zip">June KML</a>
        """
        provider = FakeAipProvider(html, today=date(2026, 6, 3))

        xml_url, kml_url, effective_date = provider._discover_current_dataset()

        self.assertTrue(xml_url.endswith("EG_AIP_DS_20260514_XML.zip"))
        self.assertTrue(kml_url.endswith("EG_AIP_DS_FULL_20260514_KML.zip"))
        self.assertEqual(effective_date, "2026-05-14")

    def test_discover_current_dataset_falls_back_to_earliest_future_when_needed(self):
        html = '<a href="ICAO_AIP/EG_AIP_DS_20260612_XML.zip">June XML</a>'
        provider = FakeAipProvider(html, today=date(2026, 6, 3))

        xml_url, kml_url, effective_date = provider._discover_current_dataset()

        self.assertTrue(xml_url.endswith("EG_AIP_DS_20260612_XML.zip"))
        self.assertIsNone(kml_url)
        self.assertEqual(effective_date, "2026-06-12")

    def test_discover_current_dataset_reports_missing_xml_link(self):
        provider = FakeAipProvider("<html>No datasets today</html>", today=date(2026, 6, 3))

        with self.assertRaisesRegex(RuntimeError, "Could not find a UK ICAO AIP Dataset XML link"):
            provider._discover_current_dataset()


if __name__ == "__main__":
    unittest.main()
