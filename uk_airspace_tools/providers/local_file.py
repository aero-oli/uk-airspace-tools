from __future__ import annotations

from pathlib import Path

from .base import AirspaceFeature, AirspaceProvider
from ..parsers.notam import parse_notams_from_xml


class LocalFileProvider(AirspaceProvider):
    provider_id = "local_file"
    display_name = "Local NOTAM XML file"

    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
        self._raw: bytes | None = None

    def fetch(self) -> bytes:
        self._raw = self.file_path.read_bytes()
        return self._raw

    def parse(self, raw: bytes) -> list[AirspaceFeature]:
        return parse_notams_from_xml(raw, source="Local XML file", source_url=str(self.file_path))

    def source_metadata(self) -> dict:
        return {
            "provider_id": self.provider_id,
            "display_name": self.display_name,
            "file_path": str(self.file_path),
            "source_url": str(self.file_path),
        }

