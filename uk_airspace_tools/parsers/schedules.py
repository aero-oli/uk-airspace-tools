from __future__ import annotations


def normalise_schedule(raw: str | None) -> str | None:
    if raw is None:
        return None
    text = " ".join(raw.split())
    return text or None

