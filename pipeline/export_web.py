"""지식 그래프(TTL)에서 SPARQL로 웹용 GeoJSON을 만든다. 원본은 항상 그래프."""
import json
import re
from collections import defaultdict
from datetime import datetime, timezone

from . import config

PREFIX = """PREFIX dt: <%s>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
PREFIX geo: <http://www.opengis.net/ont/geosparql#>
""" % config.ONT

CAT = {"WalkingTrail": "walk", "RunningCourse": "run", "BikePath": "bike",
       "ExerciseFacility": "exercise", "RestFacility": "rest", "Park": "park", "PublicToilet": "toilet",
       "HikingTrail": "hike", "Peak": "hike", "ConvenienceStore": "conv"}
ID_PREFIX = config.BASE + "id/"


def _short(iri):
    return str(iri).removeprefix(ID_PREFIX)


def _geometry(wkt):
    nums = [tuple(map(float, pair.split())) for pair in re.search(r"\((.*)\)", wkt).group(1).split(",")]
    pts = [[round(lon, 5), round(lat, 5)] for lon, lat in nums]
    return {"type": "Point", "coordinates": pts[0]} if wkt.startswith("POINT") else {"type": "LineString", "coordinates": pts}


def _rows(g, q):
    return g.query(PREFIX + q)


def export(g, path=config.WEB_DATA_PATH):
    base = {}
    for r in _rows(g, """SELECT ?s ?cls ?name ?d ?wkt ?src ?addr ?date ?info ?category ?len ?h24 WHERE {
        ?s a ?cls ; dt:distanceFromCenterKm ?d ; geo:hasGeometry/geo:asWKT ?wkt ; dt:fromDataset ?ds .
        ?ds rdfs:label ?src .
        OPTIONAL { ?s rdfs:label ?name } OPTIONAL { ?s dt:address ?addr } OPTIONAL { ?s dt:referenceDate ?date }
        OPTIONAL { ?s dt:facilityInfo ?info } OPTIONAL { ?s dt:category ?category } OPTIONAL { ?s dt:lengthKm ?len } OPTIONAL { ?s dt:open24Hours ?h24 }
        FILTER(STRSTARTS(STR(?cls), STR(dt:)))
    }"""):
        cls = str(r.cls).removeprefix(config.ONT)
        if cls not in CAT:
            continue
        key = str(r.s)
        if key in base:  # 병합된 장소는 출처가 여러 개 → 첫 출처 유지
            if str(r.src) not in base[key]["srcs"]:
                base[key]["srcs"].append(str(r.src))
            continue
        base[key] = {"id": _short(r.s), "name": str(r.name or ""), "cls": cls, "cat": CAT[cls],
                     "d": round(float(r.d), 2), "addr": str(r.addr or ""), "srcs": [str(r.src)],
                     "date": str(r.date or ""), "info": str(r.info or ""), "type": str(r.category or ""),
                     "len": float(r.len) if r.len is not None else None,
                     "h24": bool(r.h24.toPython()) if r.h24 is not None else None, "_wkt": str(r.wkt)}

    alt = defaultdict(list)
    for r in _rows(g, "SELECT ?s ?a WHERE { ?s skos:altLabel ?a }"):
        alt[str(r.s)].append(str(r.a))
    near = defaultdict(list)
    for r in _rows(g, """SELECT ?s ?t ?m WHERE { ?s dt:nearTo ?t ; dt:hasProximity ?p .
        ?p dt:proximityTarget ?t ; dt:distanceM ?m }"""):
        near[str(r.s)].append((int(r.m), str(r.t)))
    along = defaultdict(list)
    route_fac = defaultdict(list)
    for r in _rows(g, """SELECT ?f ?r ?m WHERE { ?f dt:alongRoute ?r ; dt:hasProximity ?p .
        ?p dt:proximityTarget ?r ; dt:distanceM ?m }"""):
        along[str(r.f)].append(str(r.r))
        route_fac[str(r.r)].append((int(r.m), str(r.f)))
    park = {str(r.f): str(r.p) for r in _rows(g, "SELECT ?f ?p WHERE { ?f dt:locatedInPark ?p }")}
    dong = {str(r.s): str(r.n) for r in _rows(g, "SELECT ?s ?n WHERE { ?s dt:inDistrict/rdfs:label ?n }")}

    def ref(iri, m=None):
        b = base.get(iri)
        out = {"id": _short(iri), "name": b["name"] if b else "", "cat": b["cat"] if b else ""}
        if m is not None:
            out["m"] = m
        return out

    features = []
    counts = defaultdict(int)
    for key, b in base.items():
        props = {k: v for k, v in b.items() if not k.startswith("_")}
        props["src"] = " · ".join(props.pop("srcs"))
        props["alt"] = alt.get(key, [])
        props["near"] = [ref(t, m) for m, t in sorted(near.get(key, []))[:5]]
        props["along"] = sorted({base[r]["name"] for r in along.get(key, []) if r in base and base[r]["name"]})[:5]
        props["fac"] = [ref(f, m) for m, f in sorted(route_fac.get(key, []))[:30]]
        props["park"] = base[park[key]]["name"] if key in park and park[key] in base else ""
        props["dong"] = dong.get(key, "")
        counts[b["cat"]] += 1
        features.append({"type": "Feature", "geometry": _geometry(b["_wkt"]), "properties": props})

    features.sort(key=lambda f: f["properties"]["d"])
    fc = {"type": "FeatureCollection",
          "meta": {"center": list(config.CENTER), "centerLabel": config.CENTER_LABEL, "radiusKm": config.RADIUS_KM,
                   "builtAt": datetime.now(timezone.utc).strftime("%Y-%m-%d"), "counts": dict(counts)},
          "features": features}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(fc, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return fc
