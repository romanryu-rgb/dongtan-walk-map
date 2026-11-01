"""거리 계산 유틸. 좌표는 항상 (lat, lon) 순서."""
import math

EARTH_R = 6371008.8


def haversine_m(lat1, lon1, lat2, lon2):
    p = math.radians
    a = (math.sin(p(lat2 - lat1) / 2) ** 2
         + math.cos(p(lat1)) * math.cos(p(lat2)) * math.sin(p(lon2 - lon1) / 2) ** 2)
    return 2 * EARTH_R * math.asin(math.sqrt(a))


def _project(lat, lon, lat0):
    """기준 위도 lat0 주변 등거리원통 투영 (m)."""
    x = math.radians(lon) * EARTH_R * math.cos(math.radians(lat0))
    y = math.radians(lat) * EARTH_R
    return x, y


def point_line_distance_m(lat, lon, coords):
    if len(coords) == 1:
        return haversine_m(lat, lon, *coords[0])
    px, py = _project(lat, lon, lat)
    best = float("inf")
    pts = [_project(a, b, lat) for a, b in coords]
    for (ax, ay), (bx, by) in zip(pts, pts[1:]):
        dx, dy = bx - ax, by - ay
        seg2 = dx * dx + dy * dy
        t = 0.0 if seg2 == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / seg2))
        cx, cy = ax + t * dx, ay + t * dy
        best = min(best, math.hypot(px - cx, py - cy))
    return best


def centroid(coords):
    return (sum(c[0] for c in coords) / len(coords), sum(c[1] for c in coords) / len(coords))


def to_wkt(coords):
    if len(coords) == 1:
        lat, lon = coords[0]
        return f"POINT({lon} {lat})"
    return "LINESTRING(" + ", ".join(f"{lon} {lat}" for lat, lon in coords) + ")"
