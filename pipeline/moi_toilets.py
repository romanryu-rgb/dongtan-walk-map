"""행정안전부_공중화장실정보(LOCALDATA) 화성시 파일. 사용자가 받아 data/manual/에 넣은 CSV를 쓴다.
파일에 좌표가 없어 ① 2019년 표준데이터의 같은 이름 화장실 좌표 ② 도로명 주소 ③ 건물명 순서로 위치를 찾는다.
"""
import re

from . import config
from .records import Place

DATASET = "행정안전부_공중화장실정보"
SOURCE = "moi-toilet"
MANUAL_GLOB = "공중화장실정보_*.csv"
TARGET_GU = ("동탄구", "병점구", "효행구")  # 중심 10km에 걸치는 구(만세구는 대부분 밖)
PRECISION_KO = {"building": "건물 단위", "street": "도로 단위"}


def find_files():
    return sorted((config.ROOT / "data" / "manual").glob(MANUAL_GLOB))


def norm_name(n):
    return re.sub(r"\s+", "", n or "")


def in_target_region(r):
    addr = r.get("소재지도로명주소") or r.get("소재지지번주소") or ""
    m = re.search(r"화성시\s+(\S+구)\s", addr)
    return (m.group(1) in TARGET_GU) if m else True  # 구 표기가 없으면 일단 시도(10km 필터가 다시 거름)


def address_variants(r):
    out = []
    for col in ("소재지도로명주소", "소재지지번주소"):
        addr = (r.get(col) or "").strip()
        if not addr:
            continue
        base = re.sub(r"\s*\(.*\)\s*$", "", addr).strip()
        out.append(base)
        no_gu = re.sub(r"(화성시)\s+\S+구\s+", r"\1 ", base)  # OSM엔 2026년 신설 구 이전 주소가 많음
        if no_gu != base:
            out.append(no_gu)
    name = (r.get("화장실명") or "").strip()
    if name:
        out.append(f"{name} 화성시")
        m = re.search(r"\(([^,)]+)", r.get("소재지도로명주소") or "")
        if m:
            out.append(f"{name} 화성시 {m.group(1).strip()}")
    return list(dict.fromkeys(out))


def _info(r):
    parts = []
    hours = " ".join(x for x in (r.get("개방시간"), r.get("개방시간상세")) if x)
    if hours:
        parts.append(f"개방시간: {hours}")
    m, w = r.get("남성용-장애인용대변기수") or "0", r.get("여성용-장애인용대변기수") or "0"
    parts.append(f"장애인용 대변기: 남 {m}, 여 {w}")
    if r.get("기저귀교환대유무") == "Y":
        parts.append(f"기저귀교환대: {r.get('기저귀교환대장소') or '있음'}")
    if r.get("비상벨설치여부") == "Y":
        parts.append("비상벨: 있음")
    if r.get("관리기관명"):
        parts.append(f"관리: {r['관리기관명']}")
    return parts


def toilet_places(rows, known_coords, geocode):
    """known_coords: {정규화 이름: (lat, lon)} — 2019년 표준데이터의 좌표."""
    out = []
    for r in rows:
        name = (r.get("화장실명") or "").strip()
        known = known_coords.get(norm_name(name))
        if known:
            lat, lon = known
            where = "위치: 2019년 표준데이터의 같은 화장실 좌표"
        else:
            hit = next((g for a in address_variants(r) if (g := geocode(a)) and g[2] in PRECISION_KO), None)
            if not hit:
                continue  # 동 단위로만 찾은 곳은 위치가 부정확해 넣지 않음(좌표를 지어내지 않음)
            lat, lon, precision, service = hit
            where = f"위치: 주소로 찾은 위치({PRECISION_KO[precision]}, {service})"
        out.append(Place(
            id=f"{SOURCE}-{r['관리번호']}", source=SOURCE, record_id=r["관리번호"], cls="PublicToilet", name=name,
            coords=[(lat, lon)], address=r.get("소재지도로명주소") or r.get("소재지지번주소") or "", dataset=DATASET,
            # 원본의 데이터기준일자는 오래 그대로인 경우가 많아, 실제 갱신 시점을 기준일로 쓴다
            ref_date=(r.get("데이터갱신시점") or "")[:10] or (r.get("데이터기준일자") or ""),
            extra={"category": r.get("구분명") or "", "facility_info": " / ".join(
                _info(r) + [where] + ([f"원본 데이터기준일자: {r['데이터기준일자']}"] if r.get("데이터기준일자") else []))}))
    return out


def _base_address(addr):
    return re.sub(r"\s+", "", re.sub(r"\s*\(.*\)\s*$", "", addr))


def drop_collapsed(places):
    """주소가 다른 화장실들이 정확히 같은 좌표에 모였다면 주소 검색이 번지를 못 찾고 길의 한 점을 준 것.
    위치가 틀렸다고 보고 뺀다(같은 건물 층별 화장실처럼 주소가 같으면 유지). 반환: (남긴 것, 뺀 개수)"""
    groups = {}
    for p in places:
        groups.setdefault((round(p.coords[0][0], 6), round(p.coords[0][1], 6)), []).append(p)
    kept, dropped = [], 0
    for ps in groups.values():
        known = [p for p in ps if "2019년 표준데이터" in p.extra["facility_info"]]
        if len({_base_address(p.address) for p in ps}) > 1:
            kept += known
            dropped += len(ps) - len(known)
        else:
            kept += ps
    return kept, dropped
