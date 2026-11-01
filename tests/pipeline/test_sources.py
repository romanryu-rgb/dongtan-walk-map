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
