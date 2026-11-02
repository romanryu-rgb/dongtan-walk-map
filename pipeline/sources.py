"""데이터셋 행 → Place 변환. 이름은 원본 그대로(앞뒤 공백만 제거)."""
import hashlib
import re

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
    "15012892": dict(dataset="전국공중화장실표준데이터", cls="PublicToilet", lat="LATITUDE", lon="LONGITUDE",
                     name="TOILET_NM", id=None, addr=("RDNMADR", "LNMADR"), date="REFERENCE_DATE",
                     category="TOILET_TYPE", keep=(),
                     info=(("개방시간", "OPEN_TIME"), ("남녀공용", "UNISEX_TOILET_YN"),
                           ("남성 장애인용 대변기", "MEN_HANDICAP_TOILET_BOWL_NUMBER"),
                           ("여성 장애인용 대변기", "LADIES_HANDICAP_TOILET_BOWL_NUMBER"),
                           ("기저귀교환대", "DIPERS_EXCHG_POSI"), ("비상벨", "EMG_BELL_YN"))),
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
             "walking": "WalkingTrail", "cycleway": "BikePath", "hiking": "HikingTrail", "peaks": "Peak",
             "convenience": "ConvenienceStore"}
HIKE_NAME = re.compile(r"등산|정맥|능선|산$|봉$|산길")
H24 = {"24/7", "24hours", "00:00-24:00", "Mo-Su 00:00-24:00", "24시간"}
PAVED = {"paving_stones", "asphalt", "concrete", "paved", "sett", "concrete:plates", "wood"}


def _hiking_class(el, tags):
    """산길 분류: hiking relation·등산 이름·비포장 무명길 → 등산로, 그 밖의 이름 있는 길(둘레길 등)·포장길 → 산책로."""
    if el["type"] == "relation":
        return "HikingTrail"
    name = (tags.get("name") or "").strip()
    if name:
        return "HikingTrail" if HIKE_NAME.search(name) else "WalkingTrail"
    return "WalkingTrail" if tags.get("surface") in PAVED else "HikingTrail"
OSM_CATEGORY = {("amenity", "bench"): "벤치", ("amenity", "shelter"): "쉼터",
                ("leisure", "picnic_table"): "피크닉 테이블", ("leisure", "fitness_station"): "운동기구",
                ("leisure", "track"): "트랙", ("natural", "peak"): "산 정상"}


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
        if cls == "WalkingTrail" and tags.get("footway") in ("sidewalk", "crossing"):
            continue  # 도로 인도·횡단보도는 산책로가 아님
        coords = [c for c in _osm_coords(el) if valid_coord(*c)]
        if not coords:
            continue
        if cls in ("ExerciseFacility", "RestFacility") and len(coords) > 1:
            lat = sum(c[0] for c in coords) / len(coords)
            lon = sum(c[1] for c in coords) / len(coords)
            coords = [(lat, lon)]
        rid = f"{el['type']}-{el['id']}"
        category = next((v for (k, val), v in OSM_CATEGORY.items() if tags.get(k) == val), "")
        extra = {"category": category, "osm_tags": tags}
        if tags.get("ele"):
            extra["facility_info"] = f"해발 {tags['ele']}m"
        if name == "convenience":
            oh = (tags.get("opening_hours") or "").strip()
            extra["category"] = (tags.get("brand") or "").strip()
            extra["open24h"] = oh in H24
            extra["facility_info"] = "영업시간: 24시간" if extra["open24h"] else (f"영업시간: {oh}" if oh else "영업시간 미확인")
        out.append(Place(id=f"osm-{rid}", source="osm", record_id=rid,
                         cls=_hiking_class(el, tags) if name == "hiking" else cls,
                         name=(tags.get("name") or "").strip(), coords=coords, dataset=OSM_DATASET, extra=extra))
    return out


# 공공데이터포털 '파일데이터'(시·공사 등이 올린 최신 파일). title의 _YYYYMMDD 를 기준일 기본값으로 쓴다.
FILES = {
    "15173634": dict(cls="RestFacility", name="무더위쉼터명", lat="위도", lon="경도",
                     addr=("소재지도로명주소", "소재지지번주소"), date="데이터기준일자", category_value="무더위쉼터",
                     info=(("이용가능인원", "이용가능인원수"), ("시설면적㎡", "시설면적(제곱미터)"))),
    "15126950": dict(cls="PublicToilet", name="화장실명", lat="위도", lon="경도",
                     addr=("소재지도로명주소", "소재지지번주소"), date="데이터기준일자", category="구분",
                     info=(("개방시간", "개방시간"), ("남녀공용", "남녀공용화장실여부"),
                           ("기저귀교환대", "기저귀교환대장소"), ("비상벨", "비상벨설치여부"))),
}
# 최신 파일이 덮는 지역: 그 지역 안의 옛 표준데이터 행은 버린다(merge.drop_replaced)
REPLACES = {"15173634": {"std-15013199": "화성시"}}
PARK_TOILET_PK = "15070873"


def _dataset_name(title):
    return re.sub(r"_\d{8}\s*$", "", title.strip())


def file_places(pk, data):
    m = FILES[pk]
    out = []
    for row in data["rows"]:
        c = _coord(row, m["lat"], m["lon"])
        if not c:
            continue
        name = (row.get(m["name"]) or "").strip()
        rid = _hash_id(name, row.get(m["lat"]), row.get(m["lon"]))
        extra = {"facility_info": _info(row, m["info"]),
                 "category": m.get("category_value") or (row.get(m.get("category", "")) or "").strip()}
        out.append(Place(id=f"file-{pk}-{rid}", source=f"file-{pk}", record_id=rid, cls=m["cls"], name=name,
                         coords=[c], address=_first(row, m["addr"]), dataset=_dataset_name(data["title"]),
                         ref_date=(row.get(m["date"]) or "").strip() or data["ref_date"], extra=extra))
    return out


def attach_park_toilets(places, data):
    """공원 내 화장실 목록(좌표 없음)을 같은 이름의 공원 상세 정보에 붙인다. 좌표를 지어내지 않는다."""
    by_park = {}
    for row in data["rows"]:
        nm = (row.get("화장실명") or "").strip()
        if nm:
            by_park.setdefault(nm.split("(")[0].strip(), []).append(nm)
    def norm(n):
        return re.sub(r"\s", "", n)

    parks = {}
    for p in places:
        if p.cls == "Park" and p.name:
            key = norm(p.name.split("(")[0])  # 괄호 안 관리번호는 무시
            parks.setdefault(key, p)
            parks.setdefault(key.removeprefix("동탄"), p)  # 공사 자료는 '동탄' 접두어를 생략하기도 함
    matched = 0
    for park_name, toilets in by_park.items():
        p = parks.get(norm(park_name)) or parks.get(norm(park_name).removeprefix("동탄"))
        if not p:
            continue
        note = f"공원 내 화장실 {len(toilets)}곳: {', '.join(toilets)} ({_dataset_name(data['title'])}, {data['ref_date']})"
        p.extra["facility_info"] = " / ".join(x for x in (p.extra.get("facility_info"), note) if x)
        matched += len(toilets)
    return matched
