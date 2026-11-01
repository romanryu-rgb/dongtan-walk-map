"""장소 사이 관계를 미리 계산한다: 근처, 경로 위·옆, 공원 안, 행정동."""
import math
from collections import defaultdict

from shapely.geometry import LineString, Point
from shapely.ops import polygonize, unary_union
from shapely.strtree import STRtree

from . import config
from .geo import centroid, haversine_m, point_line_distance_m

_DEG_LAT = 111195.08


def load_districts(osm_data):
    out = []
    for el in osm_data["elements"]:
        name = el.get("tags", {}).get("name")
        lines = [LineString([(g["lon"], g["lat"]) for g in m["geometry"]])
                 for m in el.get("members", []) if m.get("role") == "outer" and len(m.get("geometry", [])) > 1]
        if name and lines:
            poly = unary_union(list(polygonize(unary_union(lines))))
            if not poly.is_empty:
                out.append((name, poly))
    return out


def _park_radius_m(park):
    try:
        area = float(park.extra.get("PARK_AR") or 0)
    except ValueError:
        area = 0
    return max(30.0, math.sqrt(area / math.pi))


def compute(places, districts):
    facilities = [p for p in places if not p.is_route]
    routes = [p for p in places if p.is_route]

    # 근처: 500m 격자로 후보 축소
    cell_lat = config.NEAR_M / _DEG_LAT
    cell_lon = cell_lat / math.cos(math.radians(config.CENTER[0]))
    grid = defaultdict(list)
    for f in facilities:
        grid[(int(f.coords[0][0] / cell_lat), int(f.coords[0][1] / cell_lon))].append(f)
    cand = defaultdict(list)
    for f in facilities:
        cy, cx = int(f.coords[0][0] / cell_lat), int(f.coords[0][1] / cell_lon)
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                for g in grid[(cy + dy, cx + dx)]:
                    if g.id != f.id:
                        d = haversine_m(*f.coords[0], *g.coords[0])
                        if d <= config.NEAR_M:
                            cand[f.id].append((d, g.id))
    near = set()
    for fid, lst in cand.items():
        for d, gid in sorted(lst)[:config.NEAR_MAX]:
            a, b = sorted((fid, gid))
            near.add((a, b, int(round(d))))

    # 경로 위·옆: STRtree(경위도)로 후보, 정확 거리는 m 단위
    along = []
    if routes:
        geoms = [LineString([(c[1], c[0]) for c in r.coords]) if len(r.coords) > 1 else Point(r.coords[0][1], r.coords[0][0])
                 for r in routes]
        tree = STRtree(geoms)
        pad = config.ALONG_M / _DEG_LAT * 1.5
        for f in facilities:
            lat, lon = f.coords[0]
            for i in tree.query(Point(lon, lat).buffer(pad)):
                d = point_line_distance_m(lat, lon, routes[i].coords)
                if d <= config.ALONG_M:
                    along.append((f.id, routes[i].id, int(round(d))))

    # 공원 안: 면적으로 환산한 반경 안, 가장 가까운 공원 1개
    parks = [p for p in facilities if p.cls == "Park"]
    in_park = []
    for f in facilities:
        if f.cls == "Park":
            continue
        best = None
        for pk in parks:
            d = haversine_m(*f.coords[0], *pk.coords[0])
            if d <= _park_radius_m(pk) and (best is None or d < best[0]):
                best = (d, pk.id)
        if best:
            in_park.append((f.id, best[1]))

    # 행정동
    district = {}
    for p in places:
        lat, lon = p.coords[0] if len(p.coords) == 1 else centroid(p.coords)
        pt = Point(lon, lat)
        for name, poly in districts:
            if poly.contains(pt):
                district[p.id] = name
                break

    return {"near": sorted(near), "along": along, "in_park": in_park, "district": district}
