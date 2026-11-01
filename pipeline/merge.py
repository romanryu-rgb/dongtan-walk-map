"""10km 필터, 시설 중복 병합, 공공 자전거도로에 OSM 선 모양 붙이기."""
import hashlib
import re
from collections import defaultdict

from . import config
from .geo import haversine_m, point_line_distance_m, _project


def within_radius(places):
    out = []
    for p in places:
        d_km = round(min(point_line_distance_m(*config.CENTER, p.coords),
                         *(haversine_m(*config.CENTER, *c) for c in p.coords)) / 1000, 2)
        if d_km < config.RADIUS_KM:
            p.dist_center_km = d_km
            out.append(p)
    return out


def drop_oversized(places, max_km=50.0):
    """전국 단위 노선(중심에서 max_km 넘게 뻗는 경로)은 동네 지도에 맞지 않아 제외한다."""
    return [p for p in places
            if max(haversine_m(*config.CENTER, *c) for c in p.coords) / 1000 <= max_km]


def unique_ids(places):
    """원본 ID가 겹치는 레코드(예: 공원 관리번호 중복)를 구분한다. 이름·좌표까지 같으면 완전 중복으로 버린다."""
    seen = {}
    out = []
    for p in places:
        sig = (p.name, tuple(p.coords))
        if p.id not in seen:
            seen[p.id] = {sig}
            out.append(p)
            continue
        if sig in seen[p.id]:
            continue
        seen[p.id].add(sig)
        h = hashlib.sha1(f"{p.name}|{p.coords}".encode("utf-8")).hexdigest()[:6]
        p.id, p.record_id = f"{p.id}-{h}", f"{p.record_id}-{h}"
        out.append(p)
    return out


def _cell(lat, lon, size=0.0005):
    return int(lat / size), int(lon / size)


def dedupe(places):
    """같은 분류 시설이 MERGE_M 이내면 하나로. 공공데이터 > OSM, 공공끼리는 먼저 온 것. 경로는 병합하지 않는다."""
    order = sorted(range(len(places)), key=lambda i: (places[i].source == "osm", i))
    grid = defaultdict(list)
    kept = []
    for i in order:
        p = places[i]
        if p.is_route:
            kept.append(p)
            continue
        lat, lon = p.coords[0]
        cy, cx = _cell(lat, lon)
        target = None
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                for q in grid[(cy + dy, cx + dx)]:
                    # 같은 데이터셋 안의 서로 다른 레코드는 다른 장소로 본다(병합은 출처가 다를 때만)
                    if q.cls == p.cls and q.source != p.source and haversine_m(lat, lon, *q.coords[0]) <= config.MERGE_M:
                        target = q
                        break
        if target is None:
            grid[(cy, cx)].append(p)
            kept.append(p)
            continue
        if p.name and p.name != target.name and p.name not in target.alt_names:
            target.alt_names.append(p.name)
        target.extra.setdefault("merged_from", []).append((p.source, p.record_id, p.dataset))
    return kept


def _base_name(name):
    name = re.sub(r"\(.*?\)", "", name).strip()
    return re.sub(r"\s*[LR]$", "", name).strip()


def _t_along(seg, pt):
    (ax, ay), (bx, by) = (_project(*seg[0], seg[0][0]), _project(*seg[-1], seg[0][0]))
    px, py = _project(*pt, seg[0][0])
    dx, dy = bx - ax, by - ay
    seg2 = dx * dx + dy * dy
    return 0.0 if seg2 == 0 else ((px - ax) * dx + (py - ay) * dy) / seg2


def attach_bike_lines(public_bikes, osm_cycleways):
    used = set()
    for bike in public_bikes:
        if len(bike.coords) < 2:
            continue
        base = _base_name(bike.name)
        seg = [bike.coords[0], bike.coords[-1]]
        matched = []
        for w in osm_cycleways:
            if w.id in used:
                continue
            dists = [point_line_distance_m(*c, seg) for c in w.coords]
            named_ok = bool(w.name) and bool(base) and (base in w.name or w.name in base) and min(dists) <= config.BIKE_MATCH_M
            unnamed_ok = not w.name and max(dists) <= config.BIKE_MATCH_M
            if named_ok or unnamed_ok:
                matched.append(w)
        if matched:
            matched.sort(key=lambda w: _t_along(seg, w.coords[0]))
            bike.coords = [c for w in matched for c in w.coords]
            bike.extra["line_from_osm"] = [w.record_id for w in matched]
            used.update(w.id for w in matched)
    return public_bikes, [w for w in osm_cycleways if w.id not in used]
