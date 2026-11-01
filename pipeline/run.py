"""전체 빌드: python -m pipeline.run [--refresh]"""
import sys

from . import build_kg, config, export_web, fetch_osm, fetch_public, merge, relations, sources

# 길관광정보 지오코딩 대상 사전 필터(중심 10km에 걸칠 수 있는 시·군)
TRAIL_REGIONS = ("화성시", "오산시", "용인시", "수원시", "평택시")


def main(refresh=False):
    places = []
    for pk in sources.PUBLIC:
        ps = sources.public_places(pk, fetch_public.fetch_dataset(pk, refresh))
        print(f"[공공] {sources.PUBLIC[pk]['dataset']}: 유효 좌표 {len(ps)}")
        places += ps

    trail_data = fetch_public.fetch_dataset(sources.TRAIL_PK, refresh)
    rows = [r for r in trail_data["rows"]
            if any(k in (r.get("BEGIN_LNMADR", "") + r.get("BEGIN_RDNMADR", "")) for k in TRAIL_REGIONS)]
    trails = sources.trail_places({"rows": rows}, fetch_osm.Geocoder())
    print(f"[공공] {sources.TRAIL_DATASET}: 후보 {len(rows)} → 지오코딩 성공 {len(trails)}")
    places += trails

    osm = {}
    for name in ("fitness", "rest", "running", "walking", "cycleway"):
        osm[name] = sources.osm_places(name, fetch_osm.query(name, refresh=refresh))
        print(f"[OSM] {name}: {len(osm[name])}")

    places = merge.drop_oversized(merge.within_radius(places))
    osm = {k: merge.drop_oversized(merge.within_radius(v)) for k, v in osm.items()}
    bikes = [p for p in places if p.cls == "BikePath"]
    bikes, osm["cycleway"] = merge.attach_bike_lines(bikes, osm["cycleway"])
    print(f"[병합] 공공 자전거도로 {len(bikes)} 중 OSM 선 매칭 {sum('line_from_osm' in b.extra for b in bikes)}")
    all_places = merge.dedupe(merge.unique_ids(places + [p for v in osm.values() for p in v]))
    print(f"[10km·병합 후] {len(all_places)}")

    districts = relations.load_districts(fetch_osm.query("districts", refresh=refresh))
    rels = relations.compute(all_places, districts)
    print(f"[관계] 근처 {len(rels['near'])}, 경로상 {len(rels['along'])}, 공원 안 {len(rels['in_park'])}, "
          f"행정동 {len(rels['district'])} (동 경계 {len(districts)})")

    g = build_kg.build(all_places, rels)
    build_kg.write(g)
    print(f"[지식 DB] {config.KG_PATH.name}: 트리플 {len(g)}")
    fc = export_web.export(g)
    print(f"[웹] {config.WEB_DATA_PATH.name}: {len(fc['features'])}건 {fc['meta']['counts']}")


if __name__ == "__main__":
    main(refresh="--refresh" in sys.argv)
