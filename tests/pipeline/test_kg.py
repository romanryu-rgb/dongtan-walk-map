import json

from rdflib import Literal, Namespace
from rdflib.namespace import RDF, RDFS

from pipeline.build_kg import build
from pipeline.config import CENTER, ROOT
from pipeline.export_web import export
from pipeline.records import Place

DT = Namespace("https://romanryu-rgb.github.io/dongtan-walk-map/ontology#")
GEO = Namespace("http://www.opengis.net/ont/geosparql#")


def sample():
    park = Place(id="std-15012890-P1", source="std-15012890", record_id="P1", cls="Park", name="여울공원",
                 coords=[CENTER], dataset="전국도시공원정보표준데이터", ref_date="2026-08-06",
                 extra={"facility_info": "운동시설: 배드민턴장", "category": "근린공원"}, dist_center_km=0.0,
                 district="청계동")
    gym = Place(id="osm-node-1", source="osm", record_id="node-1", cls="ExerciseFacility", name="",
                coords=[(CENTER[0] + 0.004, CENTER[1])], dataset="OpenStreetMap", extra={"category": "운동기구"},
                dist_center_km=0.45, alt_names=["체력단련장"])
    trail = Place(id="std-15017321-T1", source="std-15017321", record_id="T1", cls="WalkingTrail",
                  name="오산천길", coords=[(CENTER[0], CENTER[1]), (CENTER[0] + 0.01, CENTER[1])],
                  dataset="전국길관광정보표준데이터", dist_center_km=0.0, extra={"length_km": "8.5"})
    rels = {"near": [("osm-node-1", "std-15012890-P1", 445)], "along": [("osm-node-1", "std-15017321-T1", 3)],
            "in_park": [("osm-node-1", "std-15012890-P1")], "district": {"std-15012890-P1": "청계동"}}
    return [park, gym, trail], rels


def test_every_place_has_core_properties():
    g = build(*sample())
    places = set(g.subjects(DT.fromDataset, None))
    assert len(places) == 3
    for s in places:
        assert g.value(s, DT.distanceFromCenterKm) is not None
        geom = g.value(s, GEO.hasGeometry)
        assert g.value(geom, GEO.asWKT) is not None
    named = [s for s in places if g.value(s, RDFS.label) is not None]
    assert len(named) == 2  # 이름 없는 OSM 시설은 라벨을 지어내지 않음


def test_near_park_exercise_query_returns_gym():
    g = build(*sample())
    q = (ROOT / "kg" / "queries" / "near_park_exercise.rq").read_text(encoding="utf-8")
    rows = list(g.query(q, initBindings={"parkName": Literal("여울공원", lang="ko")}))
    assert len(rows) == 1 and int(rows[0].distance) == 445


def test_route_facilities_query():
    g = build(*sample())
    q = (ROOT / "kg" / "queries" / "route_rest_facilities.rq").read_text(encoding="utf-8")
    rows = list(g.query(q, initBindings={"routeName": Literal("오산천길", lang="ko")}))
    assert len(rows) == 1


def test_export_geojson_from_graph(tmp_path):
    out = tmp_path / "p.geojson"
    export(build(*sample()), out)
    fc = json.loads(out.read_text(encoding="utf-8"))
    feats = {f["properties"]["id"]: f for f in fc["features"]}
    assert len(feats) == 3
    gym = feats["osm/node-1"]["properties"]
    assert gym["cat"] == "exercise" and gym["d"] == 0.45 and gym["alt"] == ["체력단련장"]
    assert gym["park"] == "여울공원" and gym["near"][0]["m"] == 445
    assert gym["along"] == ["오산천길"]
    assert feats["std-15017321/T1"]["geometry"]["type"] == "LineString"
    assert feats["std-15017321/T1"]["properties"]["cat"] == "walk"
    assert feats["std-15012890/P1"]["properties"]["dong"] == "청계동"
    assert fc["meta"]["center"] == list(CENTER) and fc["meta"]["radiusKm"] == 10.0
