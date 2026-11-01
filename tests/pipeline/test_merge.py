from pipeline.config import CENTER
from pipeline.merge import within_radius, dedupe, attach_bike_lines
from pipeline.records import Place

M_PER_DEG_LAT = 111195.08


def north(m):
    return (CENTER[0] + m / M_PER_DEG_LAT, CENTER[1])


def P(id, cls="RestFacility", coords=None, name="", source="std-1"):
    return Place(id=id, source=source, record_id=id, cls=cls, name=name, coords=coords or [north(0)],
                 dataset="ds-" + source)


def test_within_radius_excludes_10_01km_and_includes_9_99km():
    out = within_radius([P("far", coords=[north(10010)]), P("near", coords=[north(9990)])])
    assert [p.id for p in out] == ["near"]
    assert out[0].dist_center_km == 9.99


def test_route_crossing_boundary_kept_whole():
    line = [north(9000), north(15000)]
    [p] = within_radius([P("r", cls="WalkingTrail", coords=list(line))])
    assert p.coords == line and p.dist_center_km == 9.0


def test_same_name_40m_apart_not_merged():
    out = dedupe([P("a", name="중앙-12", coords=[north(100)]), P("b", name="중앙-12", coords=[north(140)])])
    assert len(out) == 2


def test_public_and_osm_bench_10m_merged_public_wins():
    pub = P("pub", name="그늘막", coords=[north(100)])
    osm = P("osm", name="벤치A", coords=[north(110)], source="osm")
    [m] = dedupe([osm, pub])
    assert m.id == "pub" and m.alt_names == ["벤치A"]
    assert m.extra["merged_from"] == [("osm", "osm", "ds-osm")]


def test_different_classes_not_merged():
    assert len(dedupe([P("a", coords=[north(100)]), P("b", cls="ExerciseFacility", coords=[north(105)])])) == 2


def test_routes_never_deduped():
    a = P("a", cls="WalkingTrail", coords=[north(0), north(100)], name="길")
    b = P("b", cls="WalkingTrail", coords=[north(100), north(200)], name="길")
    assert len(dedupe([a, b])) == 2


def test_bike_line_matched_with_osm_way_and_way_consumed():
    pub = P("pub", cls="BikePath", name="동탄대로L", coords=[north(0), north(1000)])
    way = P("w1", cls="BikePath", name="", source="osm", coords=[north(100), north(400), north(900)])
    other = P("w2", cls="BikePath", name="", source="osm", coords=[(CENTER[0], CENTER[1] + 0.05)])
    bikes, rest = attach_bike_lines([pub], [way, other])
    assert len(bikes[0].coords) > 2
    assert [p.id for p in rest] == ["w2"]


def test_bike_without_match_keeps_two_points():
    pub = P("pub", cls="BikePath", name="X", coords=[north(0), north(1000)])
    bikes, rest = attach_bike_lines([pub], [])
    assert bikes[0].coords == [north(0), north(1000)]


def test_national_scale_route_dropped():
    from pipeline.merge import drop_oversized
    huge = P("h", cls="WalkingTrail", coords=[north(0), north(300000)])
    ok = P("o", cls="WalkingTrail", coords=[north(0), north(12000)])
    assert [p.id for p in drop_oversized([huge, ok])] == ["o"]


def test_same_dataset_records_within_30m_are_not_merged():
    a = P("a", name="중앙-13", coords=[north(100)])
    b = P("b", name="중앙-10", coords=[north(105)])
    out = dedupe([a, b])
    assert len(out) == 2 and out[0].alt_names == []


def test_duplicate_source_ids_get_distinct_ids_and_exact_duplicates_dropped():
    from pipeline.merge import unique_ids
    p1 = P("std-1-X", name="가공원", coords=[north(100)])
    p2 = P("std-1-X", name="나공원", coords=[north(5000)])
    p3 = P("std-1-X", name="가공원", coords=[north(100)])
    out = unique_ids([p1, p2, p3])
    assert len(out) == 2
    assert len({p.id for p in out}) == 2 and len({p.record_id for p in out}) == 2
    assert out[0].id == "std-1-X"
