from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class AirspaceFeature:
    id: str
    source: str
    source_id: Optional[str]
    feature_type: str
    name: Optional[str]
    description: Optional[str]
    raw_text: str
    status: str
    effective_start: Optional[datetime]
    effective_end: Optional[datetime]
    retrieved_at: datetime
    geometry_quality: str
    lower_limit_raw: Optional[str]
    upper_limit_raw: Optional[str]
    lower_limit_value: Optional[float]
    upper_limit_value: Optional[float]
    lower_limit_unit: Optional[str]
    upper_limit_unit: Optional[str]
    lower_limit_reference: Optional[str]
    upper_limit_reference: Optional[str]
    lower_altitude_ft: Optional[float]
    upper_altitude_ft: Optional[float]
    qcode: Optional[str]
    traffic: Optional[str]
    scope: Optional[str]
    activity_group: Optional[str]
    radius_nm: Optional[float]
    latitude: Optional[float]
    longitude: Optional[float]
    country: Optional[str]
    fir: Optional[str]
    icao_location: Optional[str]
    source_url: Optional[str]
    geometry_wkt: Optional[str]
    parse_warnings: list[str] = field(default_factory=list)


class AirspaceProvider:
    provider_id: str = "base"
    display_name: str = "Base airspace provider"

    def fetch(self) -> bytes:
        raise NotImplementedError

    def parse(self, raw: bytes) -> list[AirspaceFeature]:
        raise NotImplementedError

    def source_metadata(self) -> dict:
        raise NotImplementedError

