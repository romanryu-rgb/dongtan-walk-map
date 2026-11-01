# 동탄 걷기·운동 지도

경기도 화성시 동탄구 청계동 552를 중심으로 반경 10km 안의 **산책로·런닝코스·자전거도로**와
그 주변 **휴게시설·운동시설·공원**을 보여 주는 휴대폰용 지도 사이트입니다.
모든 데이터는 **온톨로지(RDF/OWL) 기반 지식 DB** 하나에서 나오며, 나중에 MCP 서버로 AI 챗봇에 연결할 수 있게 설계했습니다.

- 사이트: https://romanryu-rgb.github.io/dongtan-walk-map/
- 설계 문서: [docs/specs/2026-11-01-dongtan-walk-map-design.md](docs/specs/2026-11-01-dongtan-walk-map-design.md)

## 폴더 구조

| 경로 | 내용 |
|---|---|
| `ontology/dongtan.ttl` | 온톨로지 스키마 (클래스·속성·한국어 라벨) |
| `kg/dongtan-data.ttl` | 생성된 지식 DB (유일한 원본) |
| `kg/queries/*.rq` | 예시 SPARQL 질의 (MCP/챗봇용) |
| `pipeline/` | 데이터 수집 → 정제 → 관계 계산 → 지식 DB → 웹 데이터 |
| `site/` | 정적 웹사이트 (Leaflet + OpenStreetMap) |
| `tests/` | `pytest`(파이프라인), `node --test`(웹 로직) |

## 다시 만들기

```bash
pip install -r requirements.txt
python -m pipeline.run            # 캐시(data/raw) 사용
python -m pipeline.run --refresh  # 원본 데이터를 새로 받기
python -m http.server 8000 -d site
```

테스트:

```bash
python -m pytest tests/pipeline -q
node --test tests/web/logic.test.mjs
```

## 지식 DB 구조

```
장소 dt:Place
├─ 경로 dt:Route ── 산책로 dt:WalkingTrail / 런닝코스 dt:RunningCourse / 자전거도로 dt:BikePath
└─ 시설 dt:Facility ── 휴게시설 dt:RestFacility / 운동시설 dt:ExerciseFacility / 공원 dt:Park
                     └─ 생활편의시설 dt:Amenity  (확장 지점)
```

모든 장소: `rdfs:label`(원본 이름), `skos:altLabel`(병합된 다른 이름), `dt:distanceFromCenterKm`,
`geo:hasGeometry/geo:asWKT`, `dt:fromDataset`, `dt:referenceDate`, `dt:sourceRecordId`.

관계: `dt:nearTo`(500m, 거리는 `dt:hasProximity → dt:Proximity{dt:proximityTarget, dt:distanceM}`),
`dt:alongRoute`/`dt:hasRouteFacility`(경로 100m 이내), `dt:locatedInPark`, `dt:inDistrict`.

예: "여울공원 근처 운동시설" → `kg/queries/near_park_exercise.rq` 에 `?parkName = "여울공원"@ko`.

## 데이터 출처

- 공공데이터포털 표준데이터: 전국도시공원정보, 전국실외운동기구설치정보, 전국그늘막쉼터, 전국무더위쉼터,
  전국자전거도로, 전국길관광정보 (장소 이름은 원본 그대로 사용)
- © OpenStreetMap contributors (ODbL): 운동기구·벤치·쉼터·런닝 트랙·산책로·자전거길·행정동 경계 보충
- 중심 좌표는 동탄순환대로22길(청계동 552 인근) 도로 중심점 근사값 — `pipeline/config.py` 의 `CENTER`

## 생활편의시설 추가 방법

1. `ontology/dongtan.ttl` 에 `dt:Amenity` 하위 클래스 추가 (예: `dt:PublicToilet rdfs:subClassOf dt:Amenity`)
2. `pipeline/sources.py` 의 `PUBLIC` 에 데이터셋 매핑 한 줄 추가 (예: 전국공중화장실표준데이터 pk `15012892`)
3. `pipeline/export_web.py` 의 `CAT`, `site/js/app.js` 의 `CAT`, `site/index.html` 칩에 분류 추가
4. `python -m pipeline.run`
