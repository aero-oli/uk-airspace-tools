from __future__ import annotations

import re


COMPACT_COORD_RE = re.compile(
    r"^(?P<lat_deg>\d{2})(?P<lat_min>\d{2})(?P<lat_sec>\d{0,2})(?P<lat_hemi>[NS])"
    r"(?P<lon_deg>\d{3})(?P<lon_min>\d{2})(?P<lon_sec>\d{0,2})(?P<lon_hemi>[EW])$",
    re.IGNORECASE,
)


def parse_compact_coordinate(value: str) -> tuple[float, float]:
    cleaned = value.strip().upper().replace(" ", "")
    match = COMPACT_COORD_RE.fullmatch(cleaned)
    if not match:
        raise ValueError("expected DDMM[N/S]DDDMM[E/W] or DDMMSS[N/S]DDDMMSS[E/W]")

    groups = match.groupdict()
    lat = _to_decimal(groups["lat_deg"], groups["lat_min"], groups["lat_sec"], groups["lat_hemi"])
    lon = _to_decimal(groups["lon_deg"], groups["lon_min"], groups["lon_sec"], groups["lon_hemi"])
    if not -90 <= lat <= 90:
        raise ValueError("latitude outside valid range")
    if not -180 <= lon <= 180:
        raise ValueError("longitude outside valid range")
    return lat, lon


def _to_decimal(degrees: str, minutes: str, seconds: str, hemisphere: str) -> float:
    degree_value = int(degrees)
    minute_value = int(minutes)
    second_value = int(seconds) if seconds else 0
    if minute_value >= 60 or second_value >= 60:
        raise ValueError("minutes/seconds outside valid range")
    decimal = degree_value + minute_value / 60.0 + second_value / 3600.0
    if hemisphere.upper() in {"S", "W"}:
        decimal *= -1
    return decimal

