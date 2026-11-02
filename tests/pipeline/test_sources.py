from pipeline.sources import public_places, osm_places, trail_places, valid_coord


def park_row(**kw):
    row = {"MANAGE_NO": "41590-00123", "PARK_NM": " 여울공원 ", "PARK_SE": "근린공원",
           "RDNMADR": "경기도 화성시 동탄구 노작로 147", "LNMADR": "경기도 화성시 동탄구 반송동 69",
           "LATITUDE": "37.2001", "LONGITUDE": "127.0712", "PARK_AR": "52000",
           "MVM_FCLTY": "배드민턴장+운동기구", "AMSMT_FCLTY": "", "CNVNNC_FCLTY": "화장실",
           "CLTR_FCLTY": "", "ETC_FCLTY": "", "REFERENCE_DATE": "2026-08-06", "INSTT_CODE": "4590000"}
    row.update(kw)
    return row


def test_park_row_maps_to_park_with_original_name_trimmed():
    [p] = public_places("15012890", {"rows": [park_row()]})
    assert p.cls == "Park"
    assert p.name == "여울공원"
    assert p.record_id == "41590-00123"
    assert p.id == "std-15012890-41590-00123"
    assert p.dataset == "전국도시공원정보표준데이터"
    assert p.coords == [(37.2001, 127.0712)]
    assert p.address == "경기도 화성시 동탄구 노작로 147"
    assert p.ref_date == "2026-08-06"
    assert p.extra["PARK_AR"] == "52000"
    assert "배드민턴장+운동기구" in p.extra["facility_info"]


def test_invalid_coordinates_are_dropped():
    rows = [park_row(MANAGE_NO="a", LATITUDE=""), park_row(MANAGE_NO="b", LATITUDE="0", LONGITUDE="0"),
            park_row(MANAGE_NO="c", LATITUDE="127.07", LONGITUDE="37.2"), park_row(MANAGE_NO="d")]
    assert [p.record_id for p in public_places("15012890", {"rows": rows})] == ["d"]


def test_valid_coord_korea_range():
    assert valid_coord(37.2, 127.1)
    assert not valid_coord(127.1, 37.2)
    assert not valid_coord(0, 0)


def shade_row(**kw):
    row = {"INSTL_PLC_NM": "중앙-12", "LAT": "37.2", "LOT": "127.1", "SHADE_CANOPY_TYPE": "스마트그늘막",
           "LCTN_ROAD_NM": "경기도 화성시 동탄대로 1", "LCTN_LOTNO_ADDR": "", "DATA_CRTR_YMD": "2026-08-14",
           "INSTT_CODE": "4590000"}
    row.update(kw)
    return row


def test_hash_id_is_stable_for_datasets_without_id():
    a = public_places("15129447", {"rows": [shade_row()]})[0]
    b = public_places("15129447", {"rows": [shade_row()]})[0]
    c = public_places("15129447", {"rows": [shade_row(LAT="37.3")]})[0]
    assert a.record_id == b.record_id and len(a.record_id) == 12
    assert a.record_id != c.record_id
    assert a.cls == "RestFacility" and a.extra["category"] == "스마트그늘막"


def test_bike_row_has_start_and_end_coords():
    row = {"RTE_NM": "동탄대로L", "ROAD_ST_POINT_LAT": "37.20", "ROAD_ST_POINT_LON": "127.10",
           "ROAD_ED_POINT_LAT": "37.21", "ROAD_ED_POINT_LON": "127.11", "TOTAL_LENGTH": "1.4",
           "BIKE_ROAD_TYPE": "자전거보행자겸용도로", "CRTR_YMD": "2026-08-13", "INSTT_CODE": "4590000",
           "ROAD_ST_POINT_ROAD_NM_ADDR": "", "ROAD_ST_POINT_LOTNO_ADDR": "경기도 화성시 오산동 1"}
    [p] = public_places("15100063", {"rows": [row]})
    assert p.cls == "BikePath"
    assert p.coords == [(37.20, 127.10), (37.21, 127.11)]
    assert p.extra["length_km"] == "1.4"


def trail_row(**kw):
    row = {"STRET_NM": "오산생태하천길(삼남길)", "BEGIN_LNMADR": "경기도 오산시 오산동 1", "BEGIN_RDNMADR": "",
           "STRET_LT": "8.5", "REQRE_TIME": "2시간", "COURS_INFO": "A→B", "REFERENCE_DATE": "2026-08-14",
           "INSTT_CODE": "4140000", "END_LNMADR": ""}
    row.update(kw)
    return row


def test_trail_geocode_failure_drops_record():
    assert trail_places({"rows": [trail_row()]}, lambda addr: None) == []


def test_trail_geocoded_start_point():
    [p] = trail_places({"rows": [trail_row()]}, lambda addr: (37.15, 127.07))
    assert p.cls == "WalkingTrail" and p.coords == [(37.15, 127.07)]
    assert p.name == "오산생태하천길(삼남길)"
    assert p.extra["start_only"] is True


def test_osm_bench_node_and_unnamed_kept_with_empty_name():
    data = {"elements": [{"type": "node", "id": 5, "lat": 37.2, "lon": 127.1,
                          "tags": {"amenity": "bench"}}]}
    [p] = osm_places("rest", data)
    assert p.id == "osm-node-5" and p.cls == "RestFacility" and p.name == ""
    assert p.extra["category"] == "벤치"
    assert p.dataset == "OpenStreetMap"


def test_osm_way_track_uses_geometry_as_running_course():
    data = {"elements": [{"type": "way", "id": 9, "tags": {"leisure": "track", "sport": "running", "name": "트랙"},
                          "geometry": [{"lat": 37.2, "lon": 127.1}, {"lat": 37.201, "lon": 127.101}]}]}
    [p] = osm_places("running", data)
    assert p.cls == "RunningCourse" and p.coords == [(37.2, 127.1), (37.201, 127.101)]


def test_osm_node_without_coordinates_is_skipped():
    data = {"elements": [{"type": "node", "id": 7, "tags": {"amenity": "bench"}}]}
    assert osm_places("rest", data) == []


def test_rest_query_requests_node_coordinates():
    from pipeline.fetch_osm import QUERIES
    assert "out tags;" not in QUERIES["rest"]


def test_queries_keep_relation_members_geometry():
    from pipeline.fetch_osm import QUERIES
    for name, q in QUERIES.items():
        if "relation(" in q:
            assert "out geom;" in q and "tags" not in q.split("out", 1)[1], name


def test_timeouts_are_retried(monkeypatch, tmp_path):
    import pipeline.fetch_osm as fo
    calls = []

    class Resp:
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def read(self): return b'{"elements": []}'

    def fake(req, timeout):
        calls.append(req.full_url)
        if len(calls) == 1:
            raise TimeoutError("The read operation timed out")
        return Resp()

    monkeypatch.setattr(fo.urllib.request, "urlopen", fake)
    monkeypatch.setattr(fo.time, "sleep", lambda s: None)
    monkeypatch.setattr(fo.config, "RAW_DIR", tmp_path)
    assert fo.query("x", "node(1);out;", refresh=True) == {"elements": []}
    assert len(calls) == 2 and calls[0] != calls[1]


def test_osm_sidewalks_and_crossings_are_not_trails():
    geom = [{"lat": 37.2, "lon": 127.1}, {"lat": 37.201, "lon": 127.1}]
    data = {"elements": [
        {"type": "way", "id": 1, "tags": {"highway": "footway", "footway": "sidewalk", "name": "동탄오산로"}, "geometry": geom},
        {"type": "way", "id": 2, "tags": {"highway": "footway", "footway": "crossing", "name": "동탄오산로"}, "geometry": geom},
        {"type": "way", "id": 3, "tags": {"highway": "path", "name": "동탄 둘레길"}, "geometry": geom}]}
    assert [p.name for p in osm_places("walking", data)] == ["동탄 둘레길"]


def test_toilet_row_maps_to_public_toilet():
    row = {"TOILET_NM": " 여울공원 화장실 ", "TOILET_TYPE": "공중화장실", "RDNMADR": "경기도 화성시 동탄구 노작로 147",
           "LNMADR": "", "LATITUDE": "37.2001", "LONGITUDE": "127.0712", "OPEN_TIME": "24시간",
           "UNISEX_TOILET_YN": "N", "MEN_HANDICAP_TOILET_BOWL_NUMBER": "1", "LADIES_HANDICAP_TOILET_BOWL_NUMBER": None,
           "DIPERS_EXCHG_POSI": "여자화장실", "EMG_BELL_YN": "Y", "REFERENCE_DATE": "2026-07-01", "INSTT_CODE": "4590000"}
    [p] = public_places("15012892", {"rows": [row]})
    assert p.cls == "PublicToilet" and p.name == "여울공원 화장실"
    assert p.dataset == "전국공중화장실표준데이터" and p.extra["category"] == "공중화장실"
    assert "개방시간: 24시간" in p.extra["facility_info"]
    assert "기저귀교환대: 여자화장실" in p.extra["facility_info"]
    assert not p.is_route


def _way(id, tags):
    return {"type": "way", "id": id, "tags": tags, "geometry": [{"lat": 37.2, "lon": 127.1}, {"lat": 37.201, "lon": 127.1}]}


def test_hiking_source_classifies_mountain_paths_and_walks():
    data = {"elements": [
        _way(1, {"highway": "path", "name": "한남정맥"}),
        _way(2, {"highway": "path", "name": "용뫼산 등산로"}),
        _way(3, {"highway": "path", "surface": "dirt"}),
        _way(4, {"highway": "path", "name": "동탄 둘레길"}),
        _way(5, {"highway": "path", "surface": "paving_stones"}),
        {"type": "relation", "id": 6, "tags": {"route": "hiking", "name": "무봉산 등산로"},
         "members": [{"type": "way", "geometry": [{"lat": 37.2, "lon": 127.1}, {"lat": 37.21, "lon": 127.1}]}]}]}
    got = {p.record_id: p.cls for p in osm_places("hiking", data)}
    assert got == {"way-1": "HikingTrail", "way-2": "HikingTrail", "way-3": "HikingTrail",
                   "way-4": "WalkingTrail", "way-5": "WalkingTrail", "relation-6": "HikingTrail"}


def test_peak_node_maps_to_peak_with_elevation():
    data = {"elements": [{"type": "node", "id": 8, "lat": 37.18, "lon": 127.12,
                          "tags": {"natural": "peak", "name": "무봉산", "ele": "360"}}]}
    [p] = osm_places("peaks", data)
    assert p.cls == "Peak" and p.name == "무봉산" and p.extra["category"] == "산 정상"
    assert "해발 360m" in p.extra["facility_info"] and not p.is_route


def test_walking_query_no_longer_takes_hiking_relations():
    from pipeline.fetch_osm import QUERIES
    assert "hiking" not in QUERIES["walking"] and "route=hiking" in QUERIES["hiking"]
    assert "natural=peak" in QUERIES["peaks"]


def test_convenience_store_24h_and_unknown_hours():
    data = {"elements": [
        {"type": "node", "id": 1, "lat": 37.2, "lon": 127.1, "tags": {"shop": "convenience", "name": "GS25 동탄역점", "brand": "GS25", "opening_hours": "24/7"}},
        {"type": "node", "id": 2, "lat": 37.2, "lon": 127.1, "tags": {"shop": "convenience", "name": "CU 반송점", "brand": "CU"}},
        {"type": "node", "id": 3, "lat": 37.2, "lon": 127.1, "tags": {"shop": "convenience", "name": "미니스톱", "opening_hours": "Mo-Fr 10:00-19:00"}}]}
    a, b, c = osm_places("convenience", data)
    assert a.cls == "ConvenienceStore" and a.extra["category"] == "GS25" and a.extra["open24h"] is True
    assert "영업시간: 24시간" in a.extra["facility_info"]
    assert b.extra["open24h"] is False and "영업시간 미확인" in b.extra["facility_info"]
    assert c.extra["open24h"] is False and "영업시간: Mo-Fr 10:00-19:00" in c.extra["facility_info"]


def test_hwaseong_shelter_file_maps_with_source_and_date():
    from pipeline.sources import file_places
    data = {"title": "경기도 화성시_무더위쉼터_20261016", "ref_date": "2026-10-16", "rows": [
        {"번호": "1", "무더위쉼터명": "동탄1동 행정복지센터", "시설면적(제곱미터)": "120", "이용가능인원수": "40",
         "소재지지번주소": "경기도 화성시 동탄구 반송동 1", "소재지도로명주소": "경기도 화성시 동탄구 노작로 1",
         "경도": "127.07", "위도": "37.20", "데이터기준일자": "2026-10-16"},
        {"번호": "2", "무더위쉼터명": "좌표없음", "경도": "", "위도": "", "데이터기준일자": "2026-10-16"}]}
    [p] = file_places("15173634", data)
    assert p.cls == "RestFacility" and p.name == "동탄1동 행정복지센터"
    assert p.dataset == "경기도 화성시_무더위쉼터" and p.ref_date == "2026-10-16"
    assert p.source == "file-15173634" and p.extra["category"] == "무더위쉼터"
    assert "이용가능인원: 40" in p.extra["facility_info"]


def test_file_without_date_column_uses_title_date():
    from pipeline.sources import file_places
    data = {"title": "화성도시공사_공중화장실 설치현황_20251231", "ref_date": "2025-12-31", "rows": [
        {"구분": "개방화장실", "화장실명": "홍난파생가", "소재지도로명주소": "활초리 279-3", "위도": "37.15", "경도": "126.9",
         "개방시간": "09:00~18:00", "데이터기준일자": ""}]}
    [p] = file_places("15126950", data)
    assert p.cls == "PublicToilet" and p.ref_date == "2025-12-31" and p.extra["category"] == "개방화장실"


def test_park_toilet_notes_attach_to_matching_park():
    from pipeline.sources import attach_park_toilets
    from pipeline.records import Place
    park = Place(id="p", source="std-15012890", record_id="p", cls="Park", name="센트럴파크", coords=[(37.2, 127.07)],
                 extra={"facility_info": "운동시설: 테니스장"})
    other = Place(id="q", source="std-15012890", record_id="q", cls="Park", name="여울공원", coords=[(37.2, 127.07)], extra={})
    data = {"title": "화성도시공사_화성시 공원 내 공중화장실 현황_20251231", "ref_date": "2025-12-31", "rows": [
        {"권역": "1동탄", "화장실명": "센트럴파크(테니스장)"}, {"권역": "1동탄", "화장실명": "센트럴파크(음악분수)"},
        {"권역": "2동탄", "화장실명": "없는공원(입구)"}]}
    matched = attach_park_toilets([park, other], data)
    assert matched == 2
    assert "공원 내 화장실 2곳: 센트럴파크(테니스장), 센트럴파크(음악분수)" in park.extra["facility_info"]
    assert "화성도시공사_화성시 공원 내 공중화장실 현황, 2025-12-31" in park.extra["facility_info"]
    assert "facility_info" not in other.extra


def test_park_toilet_matching_ignores_spaces_dongtan_prefix_and_brackets():
    from pipeline.sources import attach_park_toilets
    from pipeline.records import Place
    mk = lambda n: Place(id=n, source="s", record_id=n, cls="Park", name=n, coords=[(37.2, 127.07)], extra={})
    parks = [mk("벌말 체육공원"), mk("동탄센트럴파크"), mk("동탄호수공원(근린23호)")]
    data = {"title": "t_20251231", "ref_date": "2025-12-31", "rows": [
        {"화장실명": "벌말체육공원"}, {"화장실명": "센트럴파크(테니스장)"}, {"화장실명": "동탄호수공원(라크몽)"}]}
    assert attach_park_toilets(parks, data) == 3
    assert all("공원 내 화장실 1곳" in p.extra["facility_info"] for p in parks)
