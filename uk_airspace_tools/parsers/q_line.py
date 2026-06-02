from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from ..geometry.coordinate_parser import parse_compact_coordinate


@dataclass
class ParsedQLine:
    raw: str
    fir: Optional[str] = None
    qcode: Optional[str] = None
    traffic: Optional[str] = None
    purpose: Optional[str] = None
    scope: Optional[str] = None
    lower_fl: Optional[int] = None
    upper_fl: Optional[int] = None
    centre_raw: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    radius_nm: Optional[float] = None
    warnings: list[str] = field(default_factory=list)


def parse_q_line(raw_q_line: str | None) -> ParsedQLine:
    parsed = ParsedQLine(raw=(raw_q_line or "").strip())
    if not raw_q_line:
        parsed.warnings.append("Missing Q-line.")
        return parsed

    q_line = raw_q_line.strip()
    if q_line.upper().startswith("Q)"):
        q_line = q_line[2:].strip()

    parts = [part.strip() for part in q_line.split("/")]
    if len(parts) < 8:
        parsed.warnings.append(f"Q-line has {len(parts)} fields; expected at least 8.")

    parsed.fir = _part(parts, 0)
    parsed.qcode = _part(parts, 1)
    parsed.traffic = _part(parts, 2)
    parsed.purpose = _part(parts, 3)
    parsed.scope = _part(parts, 4)
    parsed.lower_fl = _parse_fl(_part(parts, 5), parsed, "lower")
    parsed.upper_fl = _parse_fl(_part(parts, 6), parsed, "upper")

    coord_radius = _part(parts, 7)
    if coord_radius:
        _parse_coord_radius(coord_radius, parsed)
    else:
        parsed.warnings.append("Q-line has no coordinate/radius field.")

    return parsed


def _part(parts: list[str], index: int) -> str | None:
    return parts[index] if index < len(parts) and parts[index] else None


def _parse_fl(value: str | None, parsed: ParsedQLine, label: str) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        parsed.warnings.append(f"Could not parse {label} flight level '{value}'.")
        return None


def _parse_coord_radius(value: str, parsed: ParsedQLine) -> None:
    cleaned = value.strip().upper()
    radius = None
    coordinate = cleaned
    if len(cleaned) >= 3 and cleaned[-3:].isdigit():
        radius = float(int(cleaned[-3:]))
        coordinate = cleaned[:-3]

    parsed.centre_raw = coordinate or None
    parsed.radius_nm = radius
    try:
        lat, lon = parse_compact_coordinate(coordinate)
        parsed.latitude = lat
        parsed.longitude = lon
    except ValueError as exc:
        parsed.warnings.append(f"Could not parse Q-line coordinate '{coordinate}': {exc}")

