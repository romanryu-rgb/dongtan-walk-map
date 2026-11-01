from rdflib import Graph
from pipeline.config import ONTOLOGY_PATH

PREFIX = "PREFIX dt: <https://romanryu-rgb.github.io/dongtan-walk-map/ontology#>\nPREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>\nPREFIX owl: <http://www.w3.org/2002/07/owl#>\n"


def g():
    graph = Graph()
    graph.parse(ONTOLOGY_PATH)
    return graph


def test_running_course_is_place():
    assert g().query(PREFIX + "ASK { dt:RunningCourse rdfs:subClassOf+ dt:Place }").askAnswer


def test_amenity_is_facility_for_future_extension():
    assert g().query(PREFIX + "ASK { dt:Amenity rdfs:subClassOf dt:Facility }").askAnswer


def test_every_class_has_korean_label():
    rows = g().query(PREFIX + """SELECT ?c WHERE { ?c a owl:Class .
        FILTER NOT EXISTS { ?c rdfs:label ?l FILTER(lang(?l)='ko') } }""")
    assert list(rows) == []


def test_core_properties_declared():
    graph = g()
    for p in ["distanceFromCenterKm", "nearTo", "alongRoute", "locatedInPark", "inDistrict",
              "fromDataset", "hasProximity", "proximityTarget", "distanceM", "referenceDate"]:
        assert graph.query(PREFIX + f"ASK {{ dt:{p} a ?t }}").askAnswer, p


def test_public_toilet_is_amenity():
    assert g().query(PREFIX + "ASK { dt:PublicToilet rdfs:subClassOf dt:Amenity }").askAnswer


def test_hiking_trail_is_route_and_peak_is_place():
    graph = g()
    assert graph.query(PREFIX + "ASK { dt:HikingTrail rdfs:subClassOf dt:Route }").askAnswer
    assert graph.query(PREFIX + "ASK { dt:Peak rdfs:subClassOf dt:Place }").askAnswer


def test_convenience_store_is_amenity_with_open24h_property():
    graph = g()
    assert graph.query(PREFIX + "ASK { dt:ConvenienceStore rdfs:subClassOf dt:Amenity }").askAnswer
    assert graph.query(PREFIX + "ASK { dt:open24Hours a ?t }").askAnswer
