from shapely.geometry import Polygon

from pipeline.config import CENTER
from pipeline.records import Place
from pipeline.relations import compute, load_districts

M = 111195.08


def north(m, east_deg=0.0):
    return (CENTER[0] + m / M, CENTER[1] + east_deg)


def F(id, m, cls="ExerciseFacility", **extra):
    return Place(id=id, source="s", record_id=id, cls=cls, name=id, coords=[north(m)], extra=extra)


def test_near_includes_450m_excludes_550m_and_no_duplicate_pairs():
    r = compute([F("a", 0), F("b", 450), F("c", 1000)], [])
    pairs = {(a, b) for a, b, _ in r["near"]}
    assert pairs == {("a", "b")}
    assert 445 <= r["near"][0][2] <= 455
    r2 = compute([F("a", 0), F("b", 550)], [])
    assert r2["near"] == []


def test_bench_80m_from_route_is_along():
    route = Place(id="r", source="s", record_id="r", cls="WalkingTrail", name="길",
                  coords=[(CENTER[0], CENTER[1]), (CENTER[0], CENTER[1] + 0.02)])
    bench = Place(id="b", source="s", record_id="b", cls="RestFacility", name="", coords=[north(80, 0.01)])
    far = Place(id="f", source="s", record_id="f", cls="RestFacility", name="", coords=[north(150, 0.01)])
    r = compute([route, bench, far], [])
    assert [(f, rt) for f, rt, _ in r["along"]] == [("b", "r")]


def test_in_park_uses_area_radius():
    park = F("p", 0, cls="Park", PARK_AR="31416")  # r = 100m
    r = compute([park, F("in", 90), F("out", 110)], [])
    assert r["in_park"] == [("in", "p")]


def test_district_point_in_polygon():
    lat, lon = CENTER
    poly = Polygon([(lon - 0.01, lat - 0.01), (lon + 0.01, lat - 0.01), (lon + 0.01, lat + 0.01), (lon - 0.01, lat + 0.01)])
    r = compute([F("a", 0), F("b", 5000)], [("청계동", poly)])
    assert r["district"] == {"a": "청계동"}


def test_load_districts_from_overpass_relation():
    lat, lon = CENTER
    ring = [{"lat": lat - 0.01, "lon": lon - 0.01}, {"lat": lat - 0.01, "lon": lon + 0.01},
            {"lat": lat + 0.01, "lon": lon + 0.01}, {"lat": lat + 0.01, "lon": lon - 0.01},
            {"lat": lat - 0.01, "lon": lon - 0.01}]
    data = {"elements": [{"type": "relation", "id": 1, "tags": {"name": "청계동"},
                          "members": [{"type": "way", "role": "outer", "geometry": ring}]}]}
    [(name, poly)] = load_districts(data)
    assert name == "청계동" and poly.contains(__import__("shapely").geometry.Point(lon, lat))
