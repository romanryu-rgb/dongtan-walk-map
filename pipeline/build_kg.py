"""Place + 관계 → RDF 지식 그래프 (kg/dongtan-data.ttl)."""
import hashlib
import re

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import DCTERMS, RDF, RDFS, SKOS, XSD

from . import config
from .geo import to_wkt

DT = Namespace(config.ONT)
GEO = Namespace("http://www.opengis.net/ont/geosparql#")
ID = Namespace(config.BASE + "id/")

DATASET_URL = {"osm": "https://www.openstreetmap.org/copyright"}


def place_iri(p):
    return ID[f"{p.source}/{p.record_id}"]


def _decimal(v):
    try:
        return Literal(str(round(float(v), 3)), datatype=XSD.decimal)
    except (TypeError, ValueError):
        return None


def build(places, rels):
    g = Graph()
    for prefix, ns in (("dt", DT), ("geo", GEO), ("skos", SKOS), ("dct", DCTERMS), ("id", ID)):
        g.bind(prefix, ns)
    iri = {p.id: place_iri(p) for p in places}
    names = {p.id: p.name for p in places}

    center = ID["center"]
    g.add((center, RDF.type, DT.Place))
    g.add((center, RDFS.label, Literal(config.CENTER_LABEL, lang="ko")))
    g.add((center, DT.distanceFromCenterKm, Literal("0", datatype=XSD.decimal)))
    g.add((center, GEO.hasGeometry, ID["center/geom"]))
    g.add((ID["center/geom"], GEO.asWKT, Literal(to_wkt([config.CENTER]), datatype=GEO.wktLiteral)))

    for p in places:
        s = iri[p.id]
        g.add((s, RDF.type, DT[p.cls]))
        if p.name:
            g.add((s, RDFS.label, Literal(p.name, lang="ko")))
        for alt in p.alt_names:
            g.add((s, SKOS.altLabel, Literal(alt, lang="ko")))
        g.add((s, DT.distanceFromCenterKm, Literal(f"{p.dist_center_km:.2f}", datatype=XSD.decimal)))
        g.add((s, DT.sourceRecordId, Literal(p.record_id)))
        geom = URIRef(str(s) + "/geom")
        g.add((s, GEO.hasGeometry, geom))
        g.add((geom, GEO.asWKT, Literal(to_wkt([(round(a, 6), round(b, 6)) for a, b in p.coords]),
                                         datatype=GEO.wktLiteral)))
        ds = ID[f"dataset/{p.source}"]
        g.add((s, DT.fromDataset, ds))
        g.add((ds, RDF.type, DT.Dataset))
        g.add((ds, RDFS.label, Literal(p.dataset, lang="ko")))
        pk = p.source.removeprefix("std-")
        g.add((ds, DCTERMS.source, URIRef(DATASET_URL.get(p.source, f"https://www.data.go.kr/data/{pk}/standard.do"))))
        for src, rid, dname in p.extra.get("merged_from", []):
            other = ID[f"dataset/{src}"]
            g.add((s, DT.fromDataset, other))
            g.add((other, RDF.type, DT.Dataset))
            g.add((other, RDFS.label, Literal(dname, lang="ko")))
        if p.address:
            g.add((s, DT.address, Literal(p.address)))
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", p.ref_date or ""):
            g.add((s, DT.referenceDate, Literal(p.ref_date, datatype=XSD.date)))
        if p.extra.get("facility_info"):
            g.add((s, DT.facilityInfo, Literal(p.extra["facility_info"])))
        if "open24h" in p.extra:
            g.add((s, DT.open24Hours, Literal(bool(p.extra["open24h"]))))
        if p.extra.get("category"):
            g.add((s, DT.category, Literal(p.extra["category"])))
        if p.extra.get("length_km") and (v := _decimal(p.extra["length_km"])) is not None:
            g.add((s, DT.lengthKm, v))

    def prox(a, b, m):
        node = URIRef(str(iri[a]) + "/prox/" + hashlib.sha1(str(iri[b]).encode()).hexdigest()[:10])
        g.add((iri[a], DT.hasProximity, node))
        g.add((node, RDF.type, DT.Proximity))
        g.add((node, DT.proximityTarget, iri[b]))
        g.add((node, DT.distanceM, Literal(m, datatype=XSD.integer)))

    for a, b, m in rels["near"]:
        g.add((iri[a], DT.nearTo, iri[b]))
        g.add((iri[b], DT.nearTo, iri[a]))
        prox(a, b, m)
        prox(b, a, m)
    for f, r, m in rels["along"]:
        g.add((iri[f], DT.alongRoute, iri[r]))
        g.add((iri[r], DT.hasRouteFacility, iri[f]))
        prox(f, r, m)
    for f, pk in rels["in_park"]:
        g.add((iri[f], DT.locatedInPark, iri[pk]))
    for pid, dname in rels["district"].items():
        d = ID[f"district/{dname}"]
        g.add((d, RDF.type, DT.District))
        g.add((d, RDFS.label, Literal(dname, lang="ko")))
        g.add((iri[pid], DT.inDistrict, d))
    return g


def write(g, path=config.KG_PATH):
    path.parent.mkdir(parents=True, exist_ok=True)
    g.serialize(destination=str(path), format="turtle", encoding="utf-8")
