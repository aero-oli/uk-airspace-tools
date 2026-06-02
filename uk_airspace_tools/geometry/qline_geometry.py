from __future__ import annotations

import math
from typing import Protocol


class _QLineLike(Protocol):
    latitude: float | None
    longitude: float | None
    radius_nm: float | None


def qline_geometry_wkt(q_line: _QLineLike) -> tuple[str | None, str, str | None]:
    if q_line.latitude is None or q_line.longitude is None:
        return None, "text_only", "No reliable Q-line geometry was available."
    if q_line.radius_nm is not None and q_line.radius_nm > 0:
        return circle_polygon_wkt(q_line.latitude, q_line.longitude, q_line.radius_nm), "qline_radius", None
    return point_wkt(q_line.latitude, q_line.longitude), "qline_point", None


def point_wkt(latitude: float, longitude: float) -> str:
    return f"POINT ({longitude:.8f} {latitude:.8f})"


def circle_polygon_wkt(latitude: float, longitude: float, radius_nm: float, vertices: int = 72) -> str:
    radius_degrees_lat = radius_nm / 60.0
    cos_lat = max(math.cos(math.radians(latitude)), 0.000001)
    radius_degrees_lon = radius_degrees_lat / cos_lat

    points = []
    for index in range(vertices):
        angle = 2 * math.pi * index / vertices
        lat = latitude + radius_degrees_lat * math.sin(angle)
        lon = longitude + radius_degrees_lon * math.cos(angle)
        points.append((lon, lat))
    points.append(points[0])
    coords = ", ".join(f"{lon:.8f} {lat:.8f}" for lon, lat in points)
    return f"POLYGON (({coords}))"

