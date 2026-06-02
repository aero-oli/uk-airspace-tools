from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import re
import xml.etree.ElementTree as ET

from ..geometry.qline_geometry import qline_geometry_wkt
from ..providers.base import AirspaceFeature
from .q_line import parse_q_line
from .vertical_limits import parse_vertical_limit


FIELD_RE = re.compile(r"(?ms)(?:^|\s)([QABCDEFG])\)\s*(.*?)(?=\s+[QABCDEFG]\)\s*|$)")
NOTAM_ID_RE = re.compile(r"\b([A-Z]\d{4}/\d{2})\b", re.IGNORECASE)


def parse_notams_from_xml(raw: bytes, source: str = "Unknown", source_url: str | None = None) -> list[AirspaceFeature]:
    text = raw.decode("utf-8", errors="replace")
    structured = _parse_structured_pib_notams(text, source=source, source_url=source_url)
    if structured:
        return structured

    candidates = _extract_xml_notam_candidates(text)
    if not candidates:
        candidates = split_notam_blocks(text)
    return [parse_notam_block(candidate, source=source, source_url=source_url) for candidate in candidates]


def parse_notams_from_text(text: str, source: str = "Unknown", source_url: str | None = None) -> list[AirspaceFeature]:
    blocks = split_notam_blocks(text)
    return [parse_notam_block(block, source=source, source_url=source_url) for block in blocks]


def parse_notam_block(raw_text: str, source: str = "Unknown", source_url: str | None = None) -> AirspaceFeature:
    retrieved_at = datetime.now(timezone.utc)
    raw_text = _normalise_raw_text(raw_text)
    warnings: list[str] = []

    notam_id = _extract_notam_id(raw_text) or _fallback_id(raw_text)
    fields = _extract_fields(raw_text)
    if not fields:
        warnings.append("Could not identify standard NOTAM fields.")

    q_line = parse_q_line(fields.get("Q"))
    warnings.extend(q_line.warnings)

    lower = parse_vertical_limit(fields.get("F") or _fl_to_vertical_raw(q_line.lower_fl))
    upper = parse_vertical_limit(fields.get("G") or _fl_to_vertical_raw(q_line.upper_fl))
    warnings.extend(lower.warnings)
    warnings.extend(upper.warnings)

    effective_start, start_warning = parse_notam_datetime(fields.get("B"), "B")
    effective_end, end_warning = parse_notam_datetime(fields.get("C"), "C")
    warnings.extend([warning for warning in [start_warning, end_warning] if warning])

    status = _derive_status(raw_text, effective_start, effective_end, retrieved_at)
    geometry_wkt, geometry_quality, geometry_warning = qline_geometry_wkt(q_line)
    if geometry_warning:
        warnings.append(geometry_warning)

    icao_location = fields.get("A") or q_line.fir
    country = icao_location[:2] if icao_location and len(icao_location) >= 2 else None
    description = fields.get("E")

    return AirspaceFeature(
        id=notam_id,
        source=source,
        source_id=notam_id,
        feature_type="NOTAM",
        name=notam_id,
        description=description,
        raw_text=raw_text,
        status=status,
        effective_start=effective_start,
        effective_end=effective_end,
        retrieved_at=retrieved_at,
        geometry_quality=geometry_quality,
        lower_limit_raw=lower.raw,
        upper_limit_raw=upper.raw,
        lower_limit_value=lower.value,
        upper_limit_value=upper.value,
        lower_limit_unit=lower.unit,
        upper_limit_unit=upper.unit,
        lower_limit_reference=lower.reference,
        upper_limit_reference=upper.reference,
        lower_altitude_ft=_altitude_ft(lower),
        upper_altitude_ft=_altitude_ft(upper),
        qcode=q_line.qcode,
        traffic=q_line.traffic,
        scope=q_line.scope or q_line.purpose,
        activity_group=_activity_group(q_line.qcode),
        radius_nm=q_line.radius_nm,
        latitude=q_line.latitude,
        longitude=q_line.longitude,
        country=country,
        fir=q_line.fir,
        icao_location=icao_location,
        source_url=source_url,
        geometry_wkt=geometry_wkt,
        parse_warnings=warnings,
    )


def split_notam_blocks(text: str) -> list[str]:
    normalised = _normalise_raw_text(text)
    id_matches = list(NOTAM_ID_RE.finditer(normalised))
    if len(id_matches) > 1:
        blocks = []
        for index, match in enumerate(id_matches):
            start = match.start()
            end = id_matches[index + 1].start() if index + 1 < len(id_matches) else len(normalised)
            block = normalised[start:end].strip()
            if block:
                blocks.append(block)
        return blocks

    q_positions = [match.start() for match in re.finditer(r"(?m)(?:^|\s)Q\)", normalised)]
    if len(q_positions) > 1:
        blocks = []
        for index, start in enumerate(q_positions):
            end = q_positions[index + 1] if index + 1 < len(q_positions) else len(normalised)
            block = normalised[start:end].strip()
            if block:
                blocks.append(block)
        return blocks

    return [normalised] if normalised.strip() else []


def parse_notam_datetime(raw: str | None, label: str) -> tuple[datetime | None, str | None]:
    if raw is None:
        return None, None
    text = raw.strip().upper()
    if not text:
        return None, None
    if text == "PERM":
        return None, None

    warning = None
    if text.endswith("EST"):
        text = text[:-3].strip()
        warning = f"{label}) is estimated (EST)."

    match = re.search(r"(\d{10})", text)
    if not match:
        return None, f"Could not parse {label}) datetime '{raw}'."

    value = match.group(1)
    try:
        year = int(value[0:2])
        century = 2000 if year < 70 else 1900
        parsed = datetime(
            century + year,
            int(value[2:4]),
            int(value[4:6]),
            int(value[6:8]),
            int(value[8:10]),
            tzinfo=timezone.utc,
        )
        return parsed, warning
    except ValueError:
        return None, f"Could not parse {label}) datetime '{raw}'."


def _extract_xml_notam_candidates(text: str) -> list[str]:
    try:
        root = ET.fromstring(text)
    except ET.ParseError:
        return []

    candidates = []
    for element in root.iter():
        combined = _normalise_raw_text(" ".join(piece for piece in element.itertext() if piece and piece.strip()))
        if _looks_like_notam_block(combined):
            candidates.append(combined)

    if not candidates:
        full_text = _normalise_raw_text(" ".join(root.itertext()))
        if _looks_like_notam_block(full_text):
            candidates = split_notam_blocks(full_text)

    shortest_by_id: dict[str, str] = {}
    for candidate in candidates:
        notam_id = _extract_notam_id(candidate) or _fallback_id(candidate)
        current = shortest_by_id.get(notam_id)
        if current is None or len(candidate) < len(current):
            shortest_by_id[notam_id] = candidate
    return list(shortest_by_id.values())


def _parse_structured_pib_notams(text: str, source: str, source_url: str | None) -> list[AirspaceFeature]:
    try:
        root = ET.fromstring(text)
    except ET.ParseError:
        return []

    features = []
    for element in root.iter():
        if _local_name(element.tag) != "Notam":
            continue
        fields = _structured_notam_fields(element)
        raw_block = _structured_fields_to_raw_notam(fields)
        if raw_block:
            features.append(parse_notam_block(raw_block, source=source, source_url=source_url))
    return features


def _structured_notam_fields(element: ET.Element) -> dict[str, str]:
    fields = {child_name: child_text for child_name, child_text in _child_text_map(element).items()}
    q_line = _first_child(element, "QLine")
    if q_line is not None:
        for key, value in _child_text_map(q_line).items():
            fields[f"QLine.{key}"] = value
    return fields


def _structured_fields_to_raw_notam(fields: dict[str, str]) -> str | None:
    notam_id = _structured_notam_id(fields)
    q_line = _structured_q_line(fields)
    item_a = fields.get("ItemA") or fields.get("QLine.FIR")
    item_b = fields.get("StartValidity")
    item_c = fields.get("EndValidity")
    item_d = fields.get("ItemD")
    item_e = fields.get("ItemE")
    item_f = fields.get("ItemF")
    item_g = fields.get("ItemG")

    if not any([notam_id, q_line, item_a, item_b, item_c, item_d, item_e, item_f, item_g]):
        return None

    notam_type = fields.get("Type")
    lines = []
    if notam_id:
        header = notam_id
        if notam_type:
            header += f" NOTAM{notam_type}"
        lines.append(header)
    if q_line:
        lines.append(f"Q) {q_line}")
    if item_a:
        lines.append(f"A) {item_a}")
    if item_b:
        lines.append(f"B) {item_b}")
    if item_c:
        suffix = " EST" if fields.get("Estimation", "").lower() == "true" else ""
        lines.append(f"C) {item_c}{suffix}")
    if item_d:
        lines.append(f"D) {item_d}")
    if item_e:
        lines.append(f"E) {item_e}")
    if item_f:
        lines.append(f"F) {item_f}")
    if item_g:
        lines.append(f"G) {item_g}")
    return "\n".join(lines)


def _structured_notam_id(fields: dict[str, str]) -> str | None:
    series = fields.get("Series")
    number = fields.get("Number")
    year = fields.get("Year")
    if series and number and year:
        return f"{series.upper()}{int(number):04d}/{int(year):02d}" if number.isdigit() and year.isdigit() else f"{series.upper()}{number}/{year}"
    return None


def _structured_q_line(fields: dict[str, str]) -> str | None:
    fir = fields.get("QLine.FIR")
    code23 = fields.get("QLine.Code23")
    code45 = fields.get("QLine.Code45")
    traffic = fields.get("QLine.Traffic")
    purpose = fields.get("QLine.Purpose")
    scope = fields.get("QLine.Scope")
    lower = fields.get("QLine.Lower")
    upper = fields.get("QLine.Upper")
    coordinate = fields.get("Coordinates")
    radius = fields.get("Radius")

    if not any([fir, code23, code45, traffic, purpose, scope, lower, upper, coordinate, radius]):
        return None

    qcode = f"Q{code23 or ''}{code45 or ''}" if code23 or code45 else ""
    coord_radius = ""
    if coordinate:
        coord_radius = coordinate.upper()
        if radius and radius.isdigit():
            coord_radius += f"{int(radius):03d}"

    return "/".join([fir or "", qcode, traffic or "", purpose or "", scope or "", lower or "", upper or "", coord_radius])


def _child_text_map(element: ET.Element) -> dict[str, str]:
    values = {}
    for child in list(element):
        text = _normalise_raw_text(" ".join(piece for piece in child.itertext() if piece and piece.strip()))
        if text:
            values[_local_name(child.tag)] = text
    return values


def _first_child(element: ET.Element, name: str) -> ET.Element | None:
    for child in list(element):
        if _local_name(child.tag) == name:
            return child
    return None


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _extract_fields(raw_text: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for match in FIELD_RE.finditer(raw_text):
        key = match.group(1).upper()
        value = " ".join(match.group(2).split())
        if value:
            fields[key] = value
    return fields


def _looks_like_notam_block(text: str) -> bool:
    upper = text.upper()
    return ("Q)" in upper and "E)" in upper) or ("NOTAM" in upper and any(f"{field})" in upper for field in "QABCDE"))


def _extract_notam_id(raw_text: str) -> str | None:
    match = NOTAM_ID_RE.search(raw_text)
    return match.group(1).upper() if match else None


def _fallback_id(raw_text: str) -> str:
    digest = hashlib.sha1(raw_text.encode("utf-8", errors="replace")).hexdigest()[:12]
    return f"NOTAM-{digest}"


def _normalise_raw_text(raw_text: str) -> str:
    return re.sub(r"\s+", " ", raw_text.replace("\r", "\n")).strip()


def _derive_status(
    raw_text: str,
    effective_start: datetime | None,
    effective_end: datetime | None,
    now: datetime,
) -> str:
    upper = raw_text.upper()
    if "CANCEL" in upper or "CNL" in upper:
        return "cancelled"
    if effective_end and effective_end < now:
        return "expired"
    if effective_start and effective_start > now:
        return "upcoming"
    if effective_start or effective_end:
        return "active"
    return "unknown"


def _activity_group(qcode: str | None) -> str:
    if not qcode:
        return "Other"

    prefix = qcode.upper()[:3]
    if prefix in {"QOB", "QOL"}:
        return "Obstacles"
    if prefix.startswith("QW"):
        return "Aerial activity"
    if prefix in {"QRD", "QRT", "QRO", "QRM", "QRP", "QRR", "QRA"}:
        return "Airspace restrictions"
    if prefix in {"QFA", "QMR", "QMX", "QMP", "QMA", "QFU", "QFE", "QFF"}:
        return "Aerodrome and runway"
    if prefix.startswith("QI") or prefix.startswith("QN") or prefix.startswith("QC") or prefix.startswith("QS") or prefix.startswith("QP"):
        return "Navigation and procedures"
    return "Other"


def _altitude_ft(limit) -> float | None:
    if limit.value is None:
        return None
    if limit.unit == "FL":
        return limit.value * 100
    if limit.unit == "FT":
        return limit.value
    return None


def _fl_to_vertical_raw(value: int | None) -> str | None:
    if value is None:
        return None
    return f"FL{value:03d}"
