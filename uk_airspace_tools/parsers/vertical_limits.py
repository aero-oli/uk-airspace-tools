from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Optional


@dataclass
class ParsedVerticalLimit:
    raw: Optional[str]
    value: Optional[float]
    unit: Optional[str]
    reference: Optional[str]
    warnings: list[str] = field(default_factory=list)


def parse_vertical_limit(raw: str | None) -> ParsedVerticalLimit:
    if raw is None:
        return ParsedVerticalLimit(raw=None, value=None, unit=None, reference=None)

    text = " ".join(raw.strip().upper().split())
    if not text:
        return ParsedVerticalLimit(raw=raw, value=None, unit=None, reference=None)

    if text in {"SFC", "SURFACE"}:
        return ParsedVerticalLimit(raw=raw, value=0.0, unit="FT", reference="SFC")
    if text == "GND":
        return ParsedVerticalLimit(raw=raw, value=0.0, unit="FT", reference="GND")
    if text in {"UNL", "UNLIMITED"}:
        return ParsedVerticalLimit(raw=raw, value=None, unit="UNL", reference=None)

    fl_match = re.fullmatch(r"FL\s?(\d{2,3})", text)
    if fl_match:
        return ParsedVerticalLimit(raw=raw, value=float(fl_match.group(1)), unit="FL", reference=None)

    bare_fl_match = re.fullmatch(r"\d{3}", text)
    if bare_fl_match:
        return ParsedVerticalLimit(raw=raw, value=float(text), unit="FL", reference=None)

    ft_match = re.fullmatch(r"(\d+(?:\.\d+)?)\s?FT(?:\s+(AMSL|AGL|ALT|SFC))?", text)
    if ft_match:
        return ParsedVerticalLimit(
            raw=raw,
            value=float(ft_match.group(1)),
            unit="FT",
            reference=ft_match.group(2),
        )

    return ParsedVerticalLimit(
        raw=raw,
        value=None,
        unit=None,
        reference=None,
        warnings=[f"Ambiguous vertical limit '{raw}' preserved as raw text."],
    )

