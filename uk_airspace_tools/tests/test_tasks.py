import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from uk_airspace_tools import tasks


class FakeProvider:
    display_name = "Fake"

    def __init__(self):
        self.resolved_url = None
        self.source_file = None
        self.fetched = False
        self.parsed_raw = None

    def fetch(self) -> bytes:
        self.fetched = True
        return b"fetched"

    def parse(self, raw: bytes) -> list:
        self.parsed_raw = raw
        return ["feature"]

    def source_metadata(self) -> dict:
        return {
            "display_name": self.display_name,
            "resolved_url": self.resolved_url,
            "source_file": self.source_file,
        }


class FakeCache:
    def __init__(self, path):
        self.path = Path(path)

    def write(self, features, metadata):
        self.features = features
        self.metadata = metadata
        return self.path


class RefreshTaskHelperTest(unittest.TestCase):
    def test_read_provider_raw_reads_local_path_and_updates_provider_source_fields(self):
        provider = FakeProvider()
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "source.xml"
            path.write_bytes(b"local data")

            raw = tasks.read_provider_raw(provider, str(path))

        self.assertEqual(raw, b"local data")
        self.assertEqual(provider.resolved_url, str(path))
        self.assertEqual(provider.source_file, "source.xml")
        self.assertFalse(provider.fetched)

    def test_read_provider_raw_uses_provider_fetch_without_local_path(self):
        provider = FakeProvider()

        raw = tasks.read_provider_raw(provider)

        self.assertEqual(raw, b"fetched")
        self.assertTrue(provider.fetched)

    def test_build_refresh_cache_parses_raw_and_adds_metadata(self):
        provider = FakeProvider()
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_path = Path(temp_dir) / "cache.gpkg"
            with patch.object(tasks, "GeoPackageCache", FakeCache):
                result = tasks.build_refresh_cache(provider, kind="notam", cache_path=cache_path)

        self.assertEqual(result.features, ["feature"])
        self.assertEqual(result.gpkg_path, cache_path)
        self.assertEqual(provider.parsed_raw, b"fetched")
        self.assertEqual(result.metadata["raw_source_bytes"], "7")
        self.assertIn("refresh_timestamp", result.metadata)

    def test_parse_refresh_data_returns_raw_features_and_metadata(self):
        provider = FakeProvider()

        parsed = tasks.parse_refresh_data(provider)

        self.assertEqual(parsed.raw, b"fetched")
        self.assertEqual(parsed.features, ["feature"])
        self.assertEqual(parsed.metadata["raw_source_bytes"], "7")


if __name__ == "__main__":
    unittest.main()
