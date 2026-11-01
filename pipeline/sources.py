"""데이터셋 행 → Place 변환. 이름은 원본 그대로(앞뒤 공백만 제거)."""
import hashlib

from .records import Place

OSM_DATASET = "OpenStreetMap"

# pk → 매핑. id=None 이면 해시 ID 사용
PUBLIC = {
    "15012890": dict(dataset="전국도시공원정보표준데이터", cls="Park", lat="LATITUDE", lon="LONGITUDE",
                     name="PARK_NM", id="MANAGE_NO", addr=("RDNMADR", "LNMADR"), date="REFERENCE_DATE",
                     category="PARK_SE", keep=("PARK_AR",),
                     info=(("운동시설", "MVM_FCLTY"), ("유희시설", "AMSMT_FCLTY"), ("편익시설", "CNVNNC_FCLTY"),
                           ("교양시설", "CLTR_FCLTY"), ("기타시설", "ETC_FCLTY"))),
    "15139207": dict(dataset="전국실외운동기구설치정보표준데이터", cls="ExerciseFacility", lat="LAT", lon="LOT",
                     name="INSTL_PLC_NM", id=None, addr=("LCTN_ROAD_NM_ADDR", "LCTN_LOTNO_ADDR"),
                     date="DATA_CRTR_YMD", category=None, keep=("SPRTGD_QTY",),
                     info=(("운동기구", "SPRTGD_NM"),)),
    "15129447": dict(dataset="전국그늘막쉼터표준데이터", cls="RestFacility", lat="LAT", lon="LOT",
                     name="INSTL_PLC_NM", id=None, addr=("LCTN_ROAD_NM", "LCTN_LOTNO_ADDR"),
                     date="DATA_CRTR_YMD", category="SHADE_CANOPY_TYPE", keep=(), info=(("세부위치", "ACTL_PSTN"),)),
    "15013199": dict(dataset="전국무더위쉼터표준데이터", cls="RestFacility", lat="LATITUDE", lon="LONGITUDE",
                     name="SHLTR_NM", id=None, addr=("RDNMADR", "LNMADR"), date="REFERENCE_DATE",
                     category="SHLTR_TYPE", keep=("ACEPTNC_POSBL_CO",), info=(("특이사항", "PARTCLR"),)),
    "15100063": dict(dataset="전국자전거도로표준데이터", cls="BikePath", lat="ROAD_ST_POINT_LAT",
                     lon="ROAD_ST_POINT_LON", lat2="ROAD_ED_POINT_LAT", lon2="ROAD_ED_POINT_LON",
                     name="RTE_NM", id=None, addr=("ROAD_ST_POINT_ROAD_NM_ADDR", "ROAD_ST_POINT_LOTNO_ADDR"),
                     date="CRTR_YMD", category="BIKE_ROAD_TYPE", keep=(), info=(("주요경유지", "MAJOR_STOPOVER"),),
                     length="TOTAL_LENGTH"),
}
TRAIL_PK = "15017321"
TRAIL_DATASET = "전국길관광정보표준데이터"


def valid_coord(lat, lon):
    return 33 < lat < 39 and 124 < lon < 132


def _coord(row, la, lo):
    try:
        lat, lon = float(row.get(la) or ""), float(row.get(lo) or "")
    except ValueError:
        return None
    return (lat, lon) if valid_coord(lat, lon) else None


def _hash_id(*parts):
    return hashlib.sha1("|".join(str(p) for p in parts).encode("utf-8")).hexdigest()[:12]


def _first(row, cols):
    for c in cols:
        v = (row.get(c) or "").strip()
        if v:
            return v
    return ""


def _info(row, pairs):
    return " / ".join(f"{label}: {row[c].strip()}" for label, c in pairs if (row.get(c) or "").strip())


def public_places(pk, data):
    m = PUBLIC[pk]
    out = []
    for row in data["rows"]:
        coords = [c for c in (_coord(row, m["lat"], m["lon"]),
                              _coord(row, m["lat2"], m["lon2"]) if "lat2" in m else None) if c]
        if not coords:
            continue
        name = (row.get(m["name"]) or "").strip()
        rid = (row.get(m["id"]) or "").strip() if m["id"] else ""
        if not rid:
            rid = _hash_id(name, row.get(m["lat"]), row.get(m["lon"]), row.get("INSTT_CODE"))
        extra = {k: row.get(k, "") for k in m["keep"]}
        extra["facility_info"] = _info(row, m["info"])
        if m["category"]:
            extra["category"] = (row.get(m["category"]) or "").strip()
        if "length" in m:
            extra["length_km"] = (row.get(m["length"]) or "").strip()
        out.append(Place(id=f"std-{pk}-{rid}", source=f"std-{pk}", record_id=rid, cls=m["cls"], name=name,
                         coords=coords, address=_first(row, m["addr"]), dataset=m["dataset"],
                         ref_date=(row.get(m["date"]) or "").strip(), extra=extra))
    return out


def trail_places(data, geocode):
    """길관광정보는 좌표가 없어 시작지점 주소를 지오코딩한다. 실패하면 제외(좌표를 지어내지 않음)."""
    out = []
    for row in data["rows"]:
        pt = None
        for col in ("BEGIN_LNMADR", "BEGIN_RDNMADR"):
            addr = (row.get(col) or "").strip()
            if addr:
                pt = geocode(addr)
                if pt:
                    break
        if not pt:
            continue
        name = (row.get("STRET_NM") or "").strip()
        rid = _hash_id(name, row.get("BEGIN_LNMADR"), row.get("INSTT_CODE"))
        out.append(Place(
            id=f"std-{TRAIL_PK}-{rid}", source=f"std-{TRAIL_PK}", record_id=rid, cls="WalkingTrail", name=name,
            coords=[pt], address=_first(row, ("BEGIN_RDNMADR", "BEGIN_LNMADR")), dataset=TRAIL_DATASET,
            ref_date=(row.get("REFERENCE_DATE") or "").strip(),
            extra={"start_only": True, "length_km": (row.get("STRET_LT") or "").strip(),
                   "facility_info": _info(row, (("소요시간", "REQRE_TIME"), ("경로", "COURS_INFO"),
                                                ("시작지점", "BEGIN_SPOT_NM"), ("종료지점", "END_SPOT_NM")))}))
    return out


OSM_CLASS = {"fitness": "ExerciseFacility", "rest": "RestFacility", "running": "RunningCourse",
             "walking": "WalkingTrail", "cycleway": "BikePath"}
OSM_CATEGORY = {("amenity", "bench"): "벤치", ("amenity", "shelter"): "쉼터",
                ("leisure", "picnic_table"): "피크닉 테이블", ("leisure", "fitness_station"): "운동기구",
                ("leisure", "track"): "트랙"}


def _osm_coords(el):
    if "lat" in el and "lon" in el:
        return [(el["lat"], el["lon"])]
    if "geometry" in el:
        return [(g["lat"], g["lon"]) for g in el["geometry"] if g]
    if "members" in el:  # relation: 멤버 way 좌표를 순서대로 이어 붙임
        return [(g["lat"], g["lon"]) for mem in el["members"] for g in mem.get("geometry", []) if g]
    if "center" in el:
        return [(el["center"]["lat"], el["center"]["lon"])]
    return []


def osm_places(name, data):
    cls = OSM_CLASS[name]
    out = []
    for el in data["elements"]:
        tags = el.get("tags", {})
        coords = [c for c in _osm_coords(el) if valid_coord(*c)]
        if not coords:
            continue
        if cls in ("ExerciseFacility", "RestFacility") and len(coords) > 1:
            lat = sum(c[0] for c in coords) / len(coords)
            lon = sum(c[1] for c in coords) / len(coords)
            coords = [(lat, lon)]
        rid = f"{el['type']}-{el['id']}"
        category = next((v for (k, val), v in OSM_CATEGORY.items() if tags.get(k) == val), "")
        out.append(Place(id=f"osm-{rid}", source="osm", record_id=rid, cls=cls, name=(tags.get("name") or "").strip(),
                         coords=coords, dataset=OSM_DATASET, extra={"category": category, "osm_tags": tags}))
    return out
