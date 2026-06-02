from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from html.parser import HTMLParser
import json
import math
import re
import xml.etree.ElementTree as ET
from io import BytesIO
from urllib.parse import urljoin
from urllib.request import Request, urlopen
from zipfile import ZipFile


DATASETS_URL = "https://nats-uk.ead-it.com/cms-nats/opencms/en/Publications/digital-datasets/"


@dataclass
class PermanentAirspaceFeature:
    id: str
    name: str | None
    designator: str | None
    airspace_type: str | None
    local_type: str | None
    category: str
    airspace_class: str | None
    lower_limit_raw: str | None
    upper_limit_raw: str | None
    lower_limit_value: float | None
    upper_limit_value: float | None
    lower_limit_unit: str | None
    upper_limit_unit: str | None
    lower_limit_reference: str | None
    upper_limit_reference: str | None
    lower_altitude_ft: float | None
    upper_altitude_ft: float | None
    activation_status: str | None
    effective_start: datetime | None
    effective_end: datetime | None
    source: str
    source_file: str | None
    source_effective_date: str | None
    remarks: str | None
    geometry_quality: str
    geometry_wkt: str | None
    raw_properties: str | None
    parse_warnings: list[str] = field(default_factory=list)


class _LinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links: list[str] = []

    def handle_starttag(self, tag, attrs):
        href = dict(attrs).get("href")
        if href:
            self.links.append(href)


class NatsAipDatasetProvider:
    provider_id = "nats_aip_dataset"
    display_name = "NATS UK ICAO AIP Dataset"

    def __init__(self, url: str | None = None, today: date | None = None, timeout: int = 60):
        self.url = url
        self.today = today or date.today()
        self.timeout = timeout
        self.resolved_url: str | None = None
        self.source_file: str | None = None
        self.effective_date: str | None = None
        self.kml_fallback_url: str | None = None

    def fetch(self) -> bytes:
        if self.url:
            self.resolved_url = self.url
        else:
            self.resolved_url, self.kml_fallback_url, self.effective_date = self._discover_current_dataset()
        return self._download(self.resolved_url)

    def parse(self, raw: bytes) -> list[PermanentAirspaceFeature]:
        features = self._parse_xml_zip(raw)
        if features:
            return features
        if self.kml_fallback_url:
            return self._parse_kml_zip(self._download(self.kml_fallback_url))
        return self._parse_kml_zip(raw)

    def source_metadata(self) -> dict:
        return {
            "provider_id": self.provider_id,
            "display_name": self.display_name,
            "resolved_url": self.resolved_url,
            "kml_fallback_url": self.kml_fallback_url,
            "source_file": self.source_file,
            "effective_date": self.effective_date,
        }

    def _discover_current_dataset(self) -> tuple[str, str | None, str | None]:
        raw = self._download(DATASETS_URL).decode("utf-8", errors="replace")
        parser = _LinkParser()
        parser.feed(raw)
        xml_links: dict[str, str] = {}
        kml_links: dict[str, str] = {}
        for href in parser.links:
            url = urljoin(DATASETS_URL, href)
            xml_match = re.search(r"ICAO_AIP/EG_AIP_DS_(\d{8})_XML\.zip$", url)
            kml_match = re.search(r"ICAO_AIP/EG_AIP_DS_FULL_(\d{8})_KML\.zip$", url)
            if xml_match:
                xml_links[xml_match.group(1)] = url
            elif kml_match:
                kml_links[kml_match.group(1)] = url

        candidates = sorted(date_text for date_text in xml_links if self._date_from_yyyymmdd(date_text) <= self.today)
        if not candidates:
            candidates = sorted(xml_links)
        if not candidates:
            raise RuntimeError("Could not find a UK ICAO AIP Dataset XML link on the NATS Digital Datasets page.")

        selected = candidates[-1]
        return xml_links[selected], kml_links.get(selected), self._iso_date_from_yyyymmdd(selected)

    def _parse_xml_zip(self, raw: bytes) -> list[PermanentAirspaceFeature]:
        try:
            with ZipFile(BytesIO(raw)) as zip_file:
                xml_name = self._select_zip_member(zip_file, ".xml", preferred="FULL")
                if not xml_name:
                    return []
                self.source_file = xml_name
                xml_raw = zip_file.read(xml_name)
        except Exception:
            xml_raw = raw

        return self._parse_xml_payload(xml_raw)

    def _parse_xml_payload(self, xml_raw: bytes) -> list[PermanentAirspaceFeature]:
        try:
            root = ET.fromstring(xml_raw)
        except ET.ParseError as exc:
            if b"<kml" in xml_raw[:1000].lower():
                return self._parse_kml_payload(xml_raw)
            raise RuntimeError(f"Could not parse AIP XML/KML dataset: {exc}") from exc

        features = []
        for airspace in root.iter():
            if _local_name(airspace.tag) != "Airspace":
                continue
            feature = self._parse_airspace(airspace)
            if feature:
                features.append(feature)
        return features

    def _parse_airspace(self, airspace) -> PermanentAirspaceFeature | None:
        time_slice = _first_descendant(airspace, "AirspaceTimeSlice")
        if time_slice is None:
            return None

        identifier = _first_child_text(airspace, "identifier")
        airspace_type = _first_child_text(time_slice, "type")
        local_type = _first_child_text(time_slice, "localType")
        designator = _first_child_text(time_slice, "designator")
        name = _first_child_text(time_slice, "name")
        class_node = _first_descendant(time_slice, "classification")
        airspace_class = _clean_text(class_node.text if class_node is not None else None)
        volume = _first_descendant(time_slice, "AirspaceVolume")
        activation = _first_descendant(time_slice, "AirspaceActivation")

        lower = _vertical_limit(volume, "lower") if volume is not None else _empty_limit()
        upper = _vertical_limit(volume, "upper") if volume is not None else _empty_limit()
        geometry_wkt, geometry_quality, warnings = _volume_geometry_wkt(volume)
        begin, end = _valid_time(time_slice)
        remarks = _notes(time_slice)

        raw_properties = {
            "identifier": identifier,
            "type": airspace_type,
            "localType": local_type,
            "designator": designator,
            "name": name,
            "class": airspace_class,
        }
        feature_id = designator or identifier or name
        if not feature_id:
            return None

        return PermanentAirspaceFeature(
            id=feature_id,
            name=name,
            designator=designator,
            airspace_type=airspace_type,
            local_type=local_type,
            category=_category_for_airspace(airspace_type, local_type, name),
            airspace_class=airspace_class,
            lower_limit_raw=lower["raw"],
            upper_limit_raw=upper["raw"],
            lower_limit_value=lower["value"],
            upper_limit_value=upper["value"],
            lower_limit_unit=lower["unit"],
            upper_limit_unit=upper["unit"],
            lower_limit_reference=lower["reference"],
            upper_limit_reference=upper["reference"],
            lower_altitude_ft=_altitude_ft(lower["value"], lower["unit"]),
            upper_altitude_ft=_altitude_ft(upper["value"], upper["unit"]),
            activation_status=_first_child_text(activation, "status") if activation is not None else None,
            effective_start=begin,
            effective_end=end,
            source=self.display_name,
            source_file=self.source_file,
            source_effective_date=self.effective_date,
            remarks=remarks,
            geometry_quality=geometry_quality,
            geometry_wkt=geometry_wkt,
            raw_properties=json.dumps(raw_properties, sort_keys=True),
            parse_warnings=warnings,
        )

    def _parse_kml_zip(self, raw: bytes) -> list[PermanentAirspaceFeature]:
        try:
            kml_raw, source_file = _extract_kml_from_zip(raw)
        except Exception:
            return self._parse_kml_payload(raw)
        self.source_file = source_file
        return self._parse_kml_payload(kml_raw)

    def _parse_kml_payload(self, kml_raw: bytes) -> list[PermanentAirspaceFeature]:
        root = ET.fromstring(kml_raw)
        features = []
        for placemark in root.iter():
            if _local_name(placemark.tag) != "Placemark":
                continue
            name = _first_child_text(placemark, "name")
            description = _first_child_text(placemark, "description")
            geometry_wkt = _kml_geometry_wkt(placemark)
            if not geometry_wkt:
                continue
            airspace_type = _infer_type_from_name(name)
            features.append(
                PermanentAirspaceFeature(
                    id=name or f"kml-{len(features) + 1}",
                    name=name,
                    designator=name,
                    airspace_type=airspace_type,
                    local_type=None,
                    category=_category_for_airspace(airspace_type, None, name),
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
                    source=self.display_name,
                    source_file=self.source_file,
                    source_effective_date=self.effective_date,
                    remarks=_strip_html(description),
                    geometry_quality="kml",
                    geometry_wkt=geometry_wkt,
                    raw_properties=None,
                )
            )
        return features

    def _download(self, url: str) -> bytes:
        request = Request(url, headers={"User-Agent": "UKAirspaceTools-QGIS/0.1"})
        with urlopen(request, timeout=self.timeout) as response:
            return response.read()

    @staticmethod
    def _select_zip_member(zip_file: ZipFile, suffix: str, preferred: str | None = None) -> str | None:
        names = [name for name in zip_file.namelist() if name.lower().endswith(suffix)]
        if preferred:
            preferred_names = [name for name in names if preferred.lower() in name.lower()]
            if preferred_names:
                return sorted(preferred_names)[0]
        return sorted(names)[0] if names else None

    @staticmethod
    def _date_from_yyyymmdd(value: str) -> date:
        return date(int(value[:4]), int(value[4:6]), int(value[6:8]))

    @staticmethod
    def _iso_date_from_yyyymmdd(value: str) -> str:
        return NatsAipDatasetProvider._date_from_yyyymmdd(value).isoformat()


def _volume_geometry_wkt(volume) -> tuple[str | None, str, list[str]]:
    if volume is None:
        return None, "text_only", ["Airspace has no AirspaceVolume geometry."]
    surface = _first_descendant(volume, "Surface")
    if surface is None:
        return None, "text_only", ["Airspace volume has no horizontal projection surface."]

    ring = []
    for segment in surface.iter():
        segment_name = _local_name(segment.tag)
        if segment_name in {"GeodesicString", "LineStringSegment"}:
            ring.extend(_segment_points(segment))
        elif segment_name == "CircleByCenterPoint":
            ring.extend(_circle_points(segment))
        elif segment_name == "ArcByCenterPoint":
            ring.extend(_arc_points(segment))

    ring = _dedupe_adjacent(ring)
    if len(ring) < 3:
        return None, "text_only", ["Airspace geometry could not be converted to a polygon."]
    if ring[0] != ring[-1]:
        ring.append(ring[0])
    coords = ", ".join(f"{lon:.8f} {lat:.8f}" for lat, lon in ring)
    return f"POLYGON (({coords}))", "aixm_polygon", []


def _segment_points(segment) -> list[tuple[float, float]]:
    points = []
    for pos in segment.iter():
        if _local_name(pos.tag) == "pos":
            point = _parse_pos(pos.text)
            if point:
                points.append(point)
    return points


def _circle_points(segment, vertices: int = 96) -> list[tuple[float, float]]:
    center = _first_pos(segment)
    radius_nm = _radius_nm(segment)
    if center is None or radius_nm is None:
        return []
    return [_offset_nm(center[0], center[1], radius_nm, bearing) for bearing in [360 * i / vertices for i in range(vertices + 1)]]


def _arc_points(segment, vertices: int = 16) -> list[tuple[float, float]]:
    center = _first_pos(segment)
    radius_nm = _radius_nm(segment)
    start = _float_child(segment, "startAngle")
    end = _float_child(segment, "endAngle")
    if center is None or radius_nm is None or start is None or end is None:
        return []
    if end < start:
        end += 360
    step_count = max(2, int(abs(end - start) / 10), vertices)
    return [_offset_nm(center[0], center[1], radius_nm, start + (end - start) * i / step_count) for i in range(step_count + 1)]


def _offset_nm(latitude: float, longitude: float, radius_nm: float, bearing_degrees: float) -> tuple[float, float]:
    angle = math.radians(bearing_degrees)
    lat = latitude + (radius_nm / 60.0) * math.cos(angle)
    cos_lat = max(math.cos(math.radians(latitude)), 0.000001)
    lon = longitude + (radius_nm / 60.0) * math.sin(angle) / cos_lat
    return lat, lon


def _first_pos(element) -> tuple[float, float] | None:
    for pos in element.iter():
        if _local_name(pos.tag) == "pos":
            return _parse_pos(pos.text)
    return None


def _parse_pos(raw: str | None) -> tuple[float, float] | None:
    parts = (raw or "").split()
    if len(parts) < 2:
        return None
    try:
        return float(parts[0]), float(parts[1])
    except ValueError:
        return None


def _radius_nm(element) -> float | None:
    radius = _float_child(element, "radius")
    if radius is None:
        return None
    radius_node = _first_child(element, "radius")
    uom = (radius_node.attrib.get("uom") if radius_node is not None else "") or ""
    if "m" == uom.lower():
        return radius / 1852.0
    return radius


def _float_child(element, name: str) -> float | None:
    child = _first_child(element, name)
    if child is None:
        return None
    try:
        return float((child.text or "").strip())
    except ValueError:
        return None


def _dedupe_adjacent(points: list[tuple[float, float]]) -> list[tuple[float, float]]:
    deduped = []
    for point in points:
        if not deduped or point != deduped[-1]:
            deduped.append(point)
    return deduped


def _vertical_limit(volume, label: str) -> dict:
    value_node = _first_child(volume, f"{label}Limit")
    reference = _first_child_text(volume, f"{label}LimitReference")
    if value_node is None:
        return _empty_limit()
    unit = value_node.attrib.get("uom")
    value = _parse_float(value_node.text)
    raw = _format_limit(value, unit, reference)
    return {"raw": raw, "value": value, "unit": unit, "reference": reference}


def _empty_limit() -> dict:
    return {"raw": None, "value": None, "unit": None, "reference": None}


def _format_limit(value: float | None, unit: str | None, reference: str | None) -> str | None:
    if value is None and not unit and not reference:
        return None
    if unit == "FL" and value is not None:
        base = f"FL{int(value):03d}"
    elif unit and value is not None:
        base = f"{value:g}{unit}"
    elif value is not None:
        base = f"{value:g}"
    else:
        base = ""
    return " ".join(part for part in [base, reference] if part)


def _altitude_ft(value: float | None, unit: str | None) -> float | None:
    if value is None:
        return None
    if unit == "FL":
        return value * 100
    if unit == "FT":
        return value
    return None


def _category_for_airspace(airspace_type: str | None, local_type: str | None, name: str | None) -> str:
    tokens = " ".join(part for part in [airspace_type, local_type, name] if part).upper()
    if any(token in tokens.split() for token in ["CTR", "CTA", "TMA"]):
        return "Controlled airspace"
    if any(token in tokens.split() for token in ["ATZ", "MATZ"]):
        return "Aerodrome zones"
    if airspace_type in {"D", "D_OTHER", "R", "P", "TRA", "TSA", "RAS"} or any(token in tokens for token in ["RESTRICTED", "DANGER", "PROHIBITED", "RPZ", "FRZ"]):
        return "Airspace restrictions"
    if any(token in tokens for token in ["RMZ", "TMZ", "FBZ"]):
        return "Radio/transponder zones"
    if any(token in tokens for token in ["ROUTE", "AIRWAY", "AWY"]):
        return "Airways/routes"
    return "Other permanent airspace"


def _valid_time(time_slice) -> tuple[datetime | None, datetime | None]:
    valid_time = _first_child(time_slice, "validTime")
    begin = _first_descendant_text(valid_time, "beginPosition") if valid_time is not None else None
    end_node = _first_descendant(valid_time, "endPosition") if valid_time is not None else None
    end = _clean_text(end_node.text if end_node is not None else None)
    return _parse_datetime(begin), _parse_datetime(end)


def _parse_datetime(value: str | None) -> datetime | None:
    value = _clean_text(value)
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _notes(element) -> str | None:
    notes = []
    for note in element.iter():
        if _local_name(note.tag) == "translatedNote":
            text = _clean_text(" ".join(note.itertext()))
            if text and text not in notes:
                notes.append(text)
    return "\n".join(notes) if notes else None


def _kml_geometry_wkt(placemark) -> str | None:
    polygons = []
    for polygon in placemark.iter():
        if _local_name(polygon.tag) != "Polygon":
            continue
        coordinates_node = _first_descendant(polygon, "coordinates")
        if coordinates_node is None:
            continue
        ring = []
        for raw_coord in (coordinates_node.text or "").split():
            parts = raw_coord.split(",")
            if len(parts) >= 2:
                try:
                    ring.append((float(parts[1]), float(parts[0])))
                except ValueError:
                    pass
        if len(ring) >= 3:
            if ring[0] != ring[-1]:
                ring.append(ring[0])
            polygons.append("((" + ", ".join(f"{lon:.8f} {lat:.8f}" for lat, lon in ring) + "))")
    if not polygons:
        return None
    if len(polygons) == 1:
        return f"POLYGON {polygons[0]}"
    return "MULTIPOLYGON (" + ", ".join(polygons) + ")"


def _extract_kml_from_zip(raw: bytes) -> tuple[bytes, str]:
    with ZipFile(BytesIO(raw)) as zip_file:
        names = zip_file.namelist()
        kml_names = [name for name in names if name.lower().endswith(".kml")]
        if kml_names:
            name = sorted(kml_names)[0]
            return zip_file.read(name), name
        kmz_names = [name for name in names if name.lower().endswith(".kmz")]
        if kmz_names:
            kmz_name = sorted(kmz_names)[0]
            with ZipFile(BytesIO(zip_file.read(kmz_name))) as kmz:
                kml_name = sorted(name for name in kmz.namelist() if name.lower().endswith(".kml"))[0]
                return kmz.read(kml_name), f"{kmz_name}/{kml_name}"
    raise RuntimeError("No KML file was found in the AIP dataset archive.")


def _infer_type_from_name(name: str | None) -> str | None:
    if not name:
        return None
    tokens = re.split(r"[\s/\\-]+", name.upper())
    for token in tokens:
        if token in {"CTR", "CTA", "TMA", "ATZ", "MATZ", "RMZ", "TMZ", "D", "R", "P"}:
            return token
    return None


def _strip_html(value: str | None) -> str | None:
    if not value:
        return None
    return _clean_text(re.sub(r"<[^>]+>", " ", value))


def _first_child(element, name: str):
    if element is None:
        return None
    for child in list(element):
        if _local_name(child.tag) == name:
            return child
    return None


def _first_child_text(element, name: str) -> str | None:
    return _clean_text(_first_child(element, name).text) if _first_child(element, name) is not None else None


def _first_descendant(element, name: str):
    if element is None:
        return None
    for child in element.iter():
        if _local_name(child.tag) == name:
            return child
    return None


def _first_descendant_text(element, name: str) -> str | None:
    node = _first_descendant(element, name)
    return _clean_text(node.text if node is not None else None)


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _clean_text(value: str | None) -> str | None:
    text = " ".join((value or "").split())
    return text or None


def _parse_float(value: str | None) -> float | None:
    try:
        return float((value or "").strip())
    except ValueError:
        return None
