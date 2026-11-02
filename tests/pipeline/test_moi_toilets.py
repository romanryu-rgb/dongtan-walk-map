from pipeline.moi_toilets import address_variants, in_target_region, toilet_places, norm_name
from pipeline.geocode import classify_photon, classify_nominatim


def row(**kw):
    r = {"관리번호": "202455300000100001", "구분명": "공중화장실", "화장실명": "병점제일타운",
         "소재지도로명주소": "경기도 화성시 병점구 경기대로 1025-5 (병점동, 병점제일타운)", "소재지지번주소": "",
         "개방시간": "정시", "개방시간상세": "11시간", "남성용-장애인용대변기수": "1", "여성용-장애인용대변기수": "1",
         "기저귀교환대유무": "N", "기저귀교환대장소": "", "비상벨설치여부": "N", "관리기관명": "민간",
         "데이터기준일자": "2024-01-29", "데이터갱신시점": "2026-05-15 18:43:46"}
    r.update(kw)
    return r


def test_address_variants_order():
    assert address_variants(row()) == [
        "경기도 화성시 병점구 경기대로 1025-5", "경기도 화성시 경기대로 1025-5",
        "병점제일타운 화성시", "병점제일타운 화성시 병점동"]


def test_target_region_is_dongtan_byeongjeom_hyohaeng():
    assert in_target_region(row())
    assert in_target_region(row(소재지도로명주소="경기도 화성시 동탄구 노작로 1"))
    assert not in_target_region(row(소재지도로명주소="경기도 화성시 만세구 우정읍 1"))


def test_norm_name():
    assert norm_name(" 노작공원 (오산천변) ") == "노작공원(오산천변)"


def test_known_coordinate_from_old_record_is_used_first():
    calls = []
    geocode = lambda a: calls.append(a) or None
    [p] = toilet_places([row()], {"병점제일타운": (37.2, 127.03)}, geocode)
    assert calls == [] and p.coords == [(37.2, 127.03)]
    assert "위치: 2019년 표준데이터의 같은 화장실 좌표" in p.extra["facility_info"]
    assert p.dataset == "행정안전부_공중화장실정보" and p.ref_date == "2026-05-15"
    assert p.record_id == "202455300000100001" and p.source == "moi-toilet"


def test_geocoded_location_and_area_level_skipped():
    hits = {"경기도 화성시 경기대로 1025-5": (37.21, 127.04, "building", "photon")}
    [p] = toilet_places([row()], {}, lambda a: hits.get(a))
    assert p.coords == [(37.21, 127.04)] and "위치: 주소로 찾은 위치(건물 단위, photon)" in p.extra["facility_info"]
    assert toilet_places([row()], {}, lambda a: (37.2, 127.0, "area", "nominatim")) == []


def test_info_fields():
    [p] = toilet_places([row()], {"병점제일타운": (37.2, 127.03)}, lambda a: None)
    info = p.extra["facility_info"]
    assert "개방시간: 정시 11시간" in info and "장애인용 대변기: 남 1, 여 1" in info and "관리: 민간" in info
    assert p.extra["category"] == "공중화장실"


def test_classify_precision():
    assert classify_photon({"properties": {"type": "house"}}) == "building"
    assert classify_photon({"properties": {"type": "locality"}}) == "area"
    assert classify_nominatim({"addresstype": "building"}) == "building"
    assert classify_nominatim({"addresstype": "quarter"}) == "area"


def test_ref_date_uses_update_time_and_keeps_original_date_in_info():
    [p] = toilet_places([row()], {"병점제일타운": (37.2, 127.03)}, lambda a: None)
    assert p.ref_date == "2026-05-15"
    assert "원본 데이터기준일자: 2024-01-29" in p.extra["facility_info"]


def test_drop_collapsed_removes_different_addresses_on_one_point_but_keeps_floors():
    from pipeline.moi_toilets import drop_collapsed
    mk = lambda i, addr, c: toilet_places([row(관리번호=str(i), 화장실명=f"t{i}", 소재지도로명주소=addr)], {},
                                          lambda a: (*c, "building", "photon"))[0]
    a = mk(1, "경기도 화성시 병점구 효행로 1144 (병점동)", (37.21, 127.03))
    b = mk(2, "경기도 화성시 병점구 효행로 1052 (병점동, 씨네)", (37.21, 127.03))
    f1 = mk(3, "경기도 화성시 동탄구 동탄대로시범길 115 (청계동, 이음터)", (37.19, 127.11))
    f2 = mk(4, "경기도 화성시 동탄구 동탄대로시범길 115 (청계동, 이음터)", (37.19, 127.11))
    solo = mk(5, "경기도 화성시 동탄구 노작로 1", (37.2, 127.07))
    kept, dropped = drop_collapsed([a, b, f1, f2, solo])
    assert sorted(p.record_id for p in kept) == ["3", "4", "5"] and dropped == 2
