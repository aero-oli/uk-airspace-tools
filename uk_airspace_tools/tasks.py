from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .storage.geopackage import GeoPackageCache
from .storage.static_geopackage import StaticAirspaceCache

try:
    from qgis.core import QgsTask
except ImportError:  # pragma: no cover - QGIS task runtime only.
    QgsTask = None


@dataclass
class RefreshResult:
    features: list
    metadata: dict
    gpkg_path: Path


@dataclass
class ParsedRefreshData:
    raw: bytes
    features: list
    metadata: dict


def read_provider_raw(provider, raw_path: str | None = None) -> bytes:
    if raw_path:
        path = Path(raw_path)
        if hasattr(provider, "resolved_url"):
            provider.resolved_url = str(path)
        if hasattr(provider, "source_file"):
            provider.source_file = path.name
        return path.read_bytes()
    return provider.fetch()


def parse_refresh_data(provider, raw_path: str | None = None) -> ParsedRefreshData:
    raw = read_provider_raw(provider, raw_path)
    features = provider.parse(raw)
    metadata = provider.source_metadata()
    metadata["raw_source_bytes"] = str(len(raw))
    metadata["refresh_timestamp"] = datetime.now(timezone.utc).isoformat()
    return ParsedRefreshData(raw=raw, features=features, metadata=metadata)


def build_refresh_cache(provider, *, kind: str, cache_path: Path, raw_path: str | None = None) -> RefreshResult:
    parsed = parse_refresh_data(provider, raw_path)
    cache_class = StaticAirspaceCache if kind == "static" else GeoPackageCache
    gpkg_path = cache_class(cache_path).write(parsed.features, parsed.metadata)
    return RefreshResult(features=parsed.features, metadata=parsed.metadata, gpkg_path=gpkg_path)


class AirspaceRefreshTask(QgsTask if QgsTask else object):
    """Fetch, parse, and write a cache without touching QGIS project layers."""

    def __init__(
        self,
        description: str,
        *,
        kind: str,
        provider,
        cache_path: Path,
        finished_callback: Callable[[object, bool], None],
        raw_path: str | None = None,
    ):
        if QgsTask is None:
            raise RuntimeError("PyQGIS is required to run refresh tasks.")
        super().__init__(description, QgsTask.CanCancel)
        self.kind = kind
        self.provider = provider
        self.cache_path = Path(cache_path)
        self.raw_path = raw_path
        self.finished_callback = finished_callback
        self.error: Exception | None = None
        self.features = []
        self.metadata: dict = {}
        self.gpkg_path: Path | None = None

    def run(self) -> bool:
        try:
            self.setProgress(5)
            raw = read_provider_raw(self.provider, self.raw_path)
            if self.isCanceled():
                return False

            self.setProgress(35)
            self.features = self.provider.parse(raw)
            if self.isCanceled():
                return False

            self.metadata = self._metadata(raw)

            self.setProgress(70)
            cache_class = StaticAirspaceCache if self.kind == "static" else GeoPackageCache
            self.gpkg_path = cache_class(self.cache_path).write(self.features, self.metadata)
            self.setProgress(100)
            return True
        except Exception as exc:  # pragma: no cover - exercised inside QGIS/runtime failures.
            self.error = exc
            return False

    def finished(self, result: bool) -> None:
        self.finished_callback(self, result)

    def _metadata(self, raw: bytes) -> dict:
        metadata = self.provider.source_metadata()
        metadata["raw_source_bytes"] = str(len(raw))
        metadata["refresh_timestamp"] = datetime.now(timezone.utc).isoformat()
        return metadata
