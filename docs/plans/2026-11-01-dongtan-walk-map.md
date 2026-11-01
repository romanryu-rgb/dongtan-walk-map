# 동탄 걷기·운동 지도 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 청계동 552 중심 반경 10km의 산책로·런닝코스·자전거도로·운동/휴게시설을 RDF 온톨로지 지식 DB로 만들고, 이를 휴대폰용 지도 웹사이트(GitHub Pages)로 보여 준다.

**Architecture:** Python 파이프라인이 공공데이터포털 표준데이터(키 없는 다운로드 엔드포인트)와 OSM Overpass를 받아 → 공통 레코드로 정규화 → 10km 필터·거리 계산·중복 병합·관계 계산 → `kg/dongtan-data.ttl`(유일한 원본)을 만든다. 같은 파이프라인이 TTL을 SPARQL로 읽어 `site/data/places.geojson`을 생성하고, 정적 사이트(Leaflet + OSM 타일)가 이를 읽는다.

**Tech Stack:** Python 3.13, rdflib 7.6, shapely 2.2, pytest(설치 필요); 웹은 빌드 도구 없는 ES 모듈 + Leaflet 1.9.4 + Leaflet.markercluster 1.5.3 (unpkg, 버전 고정); 웹 로직 테스트는 `node --test`(Node 22); 배포는 GitHub Actions → GitHub Pages.

**Spec:** `docs/specs/2026-11-01-dongtan-walk-map-design.md`

## Global Constraints

- 중심: 경기도 화성시 동탄구 청계동 552 (= 동탄순환대로22길 45, 동탄역모아미래도). 좌표 `37.19757, 127.11996` — OSM에 해당 번지가 없어 동탄순환대로22길 도로 중심점으로 근사. `pipeline/config.py`의 `CENTER` 한 곳에만 둔다.
- 반경: 중심에서 **10km 미만**(`RADIUS_KM = 10.0`, `distance < 10.0`). 경로는 가장 가까운 지점 기준, 경로는 자르지 않는다.
- API 키 사용 금지. 공공데이터는 `https://www.data.go.kr/download/columList.json?pk={pk}&ext=JSON` → `.../download/standard.json?publicDataPk={pk}&colNmList=…&totalCount&svcTableNm&perPage=10000&page={1부터}`. OSM은 `https://overpass-api.de/api/interpreter`, User-Agent `dongtan-walk-map/0.1 (github.com/romanryu-rgb)`.
- 장소 이름은 원본 그대로(공백 trim 외 변경 금지). 병합 시 다른 원본 이름은 `skos:altLabel`.
- 모든 장소: 이름, 좌표(WKT), 중심거리 km(소수 2자리), 출처 데이터셋, 기준일, 원본 레코드 ID.
- 화면·문구 한국어. 분류 버튼은 아이콘만(+`aria-label`).
- 위치 규칙: 위치 미확보(PC/거부/미지원/10초 초과) 또는 중심에서 10km 이상 → 내 위치 숨김, 중심 기준. 10km 안으로 들어오면 자동 전환.
- OSM 출처 표기: "© OpenStreetMap contributors (ODbL)". 공공데이터 출처: "공공데이터포털 {데이터셋명}".
- 네임스페이스: 스키마 `https://romanryu-rgb.github.io/dongtan-walk-map/ontology#` (prefix `dt:`), 개체 `https://romanryu-rgb.github.io/dongtan-walk-map/id/{source}/{recordId}`.

## 데이터 소스 (리컨 완료, 10km 내 건수)

| pk | 데이터셋 | 클래스 | 좌표 컬럼 | 이름 | ID | 10km |
|---|---|---|---|---|---|---|
| 15012890 | 전국도시공원정보표준데이터 | Park | LATITUDE/LONGITUDE | PARK_NM | MANAGE_NO | 733 |
| 15139207 | 전국실외운동기구설치정보표준데이터 | ExerciseFacility | LAT/LOT | INSTL_PLC_NM | 행 해시* | 23 |
| 15129447 | 전국그늘막쉼터표준데이터 | RestFacility | LAT/LOT | INSTL_PLC_NM | 행 해시* | 755 |
| 15013199 | 전국무더위쉼터표준데이터 | RestFacility | LATITUDE/LONGITUDE | SHLTR_NM | 행 해시* | 141 |
| 15100063 | 전국자전거도로표준데이터 | BikePath | 기점·종점 LAT/LON | RTE_NM | 행 해시* | 245 |
| 15017321 | 전국길관광정보표준데이터 | WalkingTrail | 없음(주소만) | STRET_NM | 행 해시* | 28 후보 |

\* ID 없는 데이터셋: `sha1(이름|위도|경도|제공기관코드)[:12]` — 재빌드 시 안정.

OSM 보충(Overpass, around:10000): `leisure=fitness_station` → ExerciseFacility, `amenity=bench|shelter` → RestFacility, `leisure=track` + `sport=running` 및 `route=running` relation → RunningCourse, `route=hiking|foot` relation·이름 있는 `highway=footway|path` 묶음 → WalkingTrail, `highway=cycleway` 또는 `bicycle=designated` way → 자전거 선 모양 매칭 + 미매칭은 BikePath(OSM), 행정동 경계 `boundary=administrative` `admin_level=8`(동).

## File Structure

```
pipeline/
  config.py            CENTER, RADIUS_KM, 경로·URL 상수, NEAR_M=500, ALONG_M=100, MERGE_M=30
  geo.py               haversine_m, point_line_distance_m, centroid, wkt
  records.py           Place dataclass (공통 레코드)
  fetch_public.py      data.go.kr 표준데이터 다운로드 + 캐시(data/raw/std_{pk}.json)
  fetch_osm.py         Overpass 질의 + 캐시(data/raw/osm_{name}.json)
  sources.py           데이터셋별 행 → Place 변환(매핑 표), 길관광 주소 지오코딩
  merge.py             10km 필터, 중복 병합, 자전거 선 매칭
  relations.py         nearTo / alongRoute / locatedInPark / inDistrict 계산
  build_kg.py          Place+관계 → rdflib Graph → kg/dongtan-data.ttl
  export_web.py        TTL → SPARQL → site/data/places.geojson
  run.py               전체 실행 (python -m pipeline.run [--offline])
ontology/dongtan.ttl   OWL 스키마 (클래스·속성·한국어 라벨)
kg/dongtan-data.ttl    생성된 지식 DB (커밋)
kg/queries/*.rq        예시 SPARQL ("여울공원 근처 운동시설" 등, MCP용)
site/index.html, site/css/app.css
site/js/logic.js       순수 함수(테스트 대상)
site/js/app.js         지도·목록·위치·UI
site/data/places.geojson (생성, 커밋)
tests/pipeline/test_*.py, tests/web/logic.test.mjs
.github/workflows/pages.yml
requirements.txt, .gitignore(data/raw/, .superpowers/, __pycache__/), README.md
```

## Review Focus

1. 위치가 10km 경계에서 왔다 갔다 할 때(9.98↔10.02km) 화면이 깜빡이며 모드가 반복 전환됨 → 0.2km 히스테리시스(들어올 때 <10.0, 나갈 때 ≥10.2)로 한 번만 전환. Task 7 테스트.
2. 좌표가 빈 값·"0"·위경도 뒤바뀜(위도>90 혹은 한국 범위 밖)인 공공데이터 행 → 조용히 버리고 건수 로그. Task 3 테스트.
3. 같은 이름 다른 장소(예: "중앙-12" 그늘막이 여러 시)·이름이 같은데 30m 넘게 떨어진 경우 → 병합하지 않음. Task 4 테스트.
4. 길관광 주소 지오코딩 실패/10km 밖 → 레코드 제외(지어낸 좌표 금지), 로그. Task 3 테스트.
5. 네이버 지도 앱 미설치 안드로이드/PC → 웹 네이버 지도 검색으로 열림. Task 7 테스트(`naverLinks`)와 Task 9 실기 확인.

---

### Task 1: 프로젝트 골격 + 지오 유틸

**Files:**
- Create: `requirements.txt`(rdflib==7.6.0, shapely==2.2.0, pytest), `.gitignore`, `pipeline/__init__.py`, `pipeline/config.py`, `pipeline/geo.py`, `pipeline/records.py`
- Test: `tests/pipeline/test_geo.py`

**Interfaces:**
- Produces:
  - `config.CENTER: tuple[float,float] = (37.19757, 127.11996)` (lat, lon), `RADIUS_KM=10.0`, `NEAR_M=500`, `ALONG_M=100`, `MERGE_M=30`, `BASE="https://romanryu-rgb.github.io/dongtan-walk-map/"`
  - `geo.haversine_m(lat1, lon1, lat2, lon2) -> float`
  - `geo.point_line_distance_m(lat, lon, coords: list[tuple[float,float]]) -> float` (coords=(lat,lon) 목록, 1개면 점 거리; 로컬 등거리원통 투영으로 선분 최소거리)
  - `geo.to_wkt(coords) -> str` (1개 → `POINT(lon lat)`, 2개 이상 → `LINESTRING(...)`)
  - `records.Place` dataclass: `id:str, source:str, record_id:str, cls:str, name:str, coords:list[tuple[float,float]], address:str="", dataset:str="", ref_date:str="", alt_names:list[str]=[], extra:dict={}, dist_center_km:float|None=None, district:str|None=None`; `cls` ∈ `WalkingTrail, RunningCourse, BikePath, RestFacility, ExerciseFacility, Park`

- [ ] **Step 1:** `git init`, `pip install -r requirements.txt`, `.gitignore` 작성.
- [ ] **Step 2: 실패 테스트**
```python
def test_haversine_known():           # 동탄역→오산역 대략 6.0km
    assert 5800 < haversine_m(37.2001,127.0960,37.1452,127.0670) < 6800
def test_point_line_distance_perpendicular():
    line=[(37.0,127.0),(37.0,127.01)]
    assert abs(point_line_distance_m(37.001,127.005,line)-111.2) < 2
def test_point_line_single_point_equals_haversine(): ...
def test_wkt_point_lon_first():
    assert to_wkt([(37.1,127.2)]) == "POINT(127.2 37.1)"
```
- [ ] **Step 3:** `python -m pytest tests/pipeline/test_geo.py -v` → FAIL(import)
- [ ] **Step 4:** 구현
- [ ] **Step 5:** 테스트 PASS → commit `feat: project skeleton and geo utils`

### Task 2: 온톨로지 스키마

**Files:** Create `ontology/dongtan.ttl`; Test `tests/pipeline/test_ontology.py`

**Interfaces:**
- Produces (모두 `dt:` 접두, 각각 `rdfs:label "…"@ko`):
  - 클래스: `Place`; `Route ⊑ Place`(`WalkingTrail`,`RunningCourse`,`BikePath` ⊑ Route); `Facility ⊑ Place`(`RestFacility`,`ExerciseFacility`,`Park`,`Amenity` ⊑ Facility); `District`; `Dataset`; `Proximity`(거리 관계 노드).
  - 데이터 속성: `distanceFromCenterKm`(xsd:decimal), `address`, `referenceDate`(xsd:date), `sourceRecordId`, `facilityInfo`(공원보유시설 원문 등 문자열), `lengthKm`.
  - 객체 속성: `fromDataset`→Dataset, `inDistrict`→District, `locatedInPark`→Park, `alongRoute`(Facility→Route), `hasRouteFacility`(inverse of alongRoute), `nearTo`(Facility↔Facility, symmetric, 거리 없는 단축 링크), `hasProximity`→Proximity, `proximityTarget`→Place, `distanceM`(xsd:integer, Proximity의 속성).
  - 기하: GeoSPARQL `geo:hasGeometry`/`geo:asWKT` 사용(`geo: <http://www.opengis.net/ont/geosparql#>`). 이름: `rdfs:label @ko`, 별칭 `skos:altLabel`.
- [ ] **Step 1: 실패 테스트** — rdflib로 파싱; `dt:RunningCourse rdfs:subClassOf+ dt:Place` SPARQL ASK가 True; `dt:Amenity rdfs:subClassOf dt:Facility`; 모든 `owl:Class`에 `@ko` 라벨 존재.
- [ ] **Step 2:** FAIL 확인 → **Step 3:** 작성 → **Step 4:** PASS → commit `feat: ontology schema`

### Task 3: 데이터 수집 + 소스 매핑

**Files:** Create `pipeline/fetch_public.py`, `pipeline/fetch_osm.py`, `pipeline/sources.py`; Test `tests/pipeline/test_sources.py` (고정 샘플 행 사용, 네트워크 없음)

**Interfaces:**
- Consumes: `records.Place`, `config`
- Produces:
  - `fetch_public.fetch_dataset(pk:str, refresh=False) -> dict` (`{"header":…, "rows":[…]}`; 페이지 1부터, 캐시 `data/raw/std_{pk}.json`)
  - `fetch_osm.query(name:str, ql:str, refresh=False) -> dict` (캐시 `data/raw/osm_{name}.json`; 429/504 시 30초 대기 후 3회 재시도); `fetch_osm.QUERIES: dict[str,str]`(위 OSM 보충 목록 + 동 경계 `out geom`)
  - `sources.public_places(pk, data) -> list[Place]` (위 표의 매핑; 공원은 `extra`에 `PARK_SE`, `PARK_AR`, 보유시설 5종 원문; 자전거는 coords=[기점,종점], `extra.TOTAL_LENGTH`, `BIKE_ROAD_TYPE`; 운동기구는 `extra.SPRTGD_NM`)
  - `sources.osm_places(name, data) -> list[Place]` (이름 없으면 OSM 태그 기반 원문 대체 없이 `name=""` → 화면에서 분류명 표시; relation/way 선은 `out geom` 좌표 사용)
  - `sources.trail_places(data, geocode) -> list[Place]` (`geocode(addr)->(lat,lon)|None`, 실제 구현은 Nominatim 1초 간격 + 캐시 `data/raw/geocode.json`; 시작지점 지번→도로명 순 시도; 실패 시 제외)
  - `sources.valid_coord(lat, lon) -> bool` (33<lat<39, 124<lon<132)
- [ ] **Step 1: 실패 테스트** — 공원 샘플 행 → `Place(cls="Park", name="여울공원", record_id=MANAGE_NO, dataset="전국도시공원정보표준데이터")`; 좌표 `""`/`"0"`/뒤바뀜 행은 결과에 없음; 이름 앞뒤 공백만 trim; 자전거 행 coords 2개; 길관광 geocode가 None이면 제외; ID 없는 데이터셋 해시가 같은 입력에 동일.
- [ ] **Step 2:** FAIL → **Step 3:** 구현 → **Step 4:** PASS
- [ ] **Step 5:** 실제 다운로드 1회 수행(`python -m pipeline.fetch_public` 대상 6개, OSM 질의) 후 건수 출력 확인 → commit `feat: data fetch and source mapping`

### Task 4: 필터·병합·자전거 선 매칭

**Files:** Create `pipeline/merge.py`; Test `tests/pipeline/test_merge.py`

**Interfaces:**
- Produces:
  - `merge.within_radius(places) -> list[Place]` (`dist_center_km` 설정 = `point_line_distance_m(CENTER, coords)/1000`, 2자리 반올림, `<10.0`만)
  - `merge.dedupe(places) -> list[Place]` (같은 cls이고 `MERGE_M` 이내 → 하나로: 공공데이터가 OSM보다 우선, 공공끼리는 먼저 온 것; 진 쪽 이름은 `alt_names`, 출처는 `extra["merged_from"]` 리스트에 `(source, record_id, dataset)`)
  - `merge.attach_bike_lines(public_bikes, osm_cycleways) -> tuple[list[Place], list[Place]]` (공공 노선의 기점-종점 선분에서 50m 이내이고 이름 일치(공공 RTE_NM에서 끝의 ` L`/`L`/`R`/`(…)` 제거 후 OSM name 포함 관계) 하는 OSM way들을 이어 공공 Place.coords로 대체; 사용된 OSM way는 두 번째 리스트에서 제거; 매칭 없으면 coords 그대로 2점)
- [ ] **Step 1: 실패 테스트** — 10.01km 점 제외, 9.99km 포함; 경계 걸친 선은 가까운 끝이 9km면 포함·좌표 불변; 같은 이름 40m 떨어진 두 그늘막 → 2개 유지; 공공+OSM 벤치 10m → 1개, OSM 이름이 alt_names에; 자전거 매칭 시 coords 길이 >2 & 사용 OSM way 제거.
- [ ] **Step 2–4:** FAIL → 구현 → PASS → commit `feat: radius filter, dedupe, bike line matching`

### Task 5: 관계 계산

**Files:** Create `pipeline/relations.py`; Test `tests/pipeline/test_relations.py`

**Interfaces:**
- Produces: `relations.compute(places, districts) -> dict` with keys
  - `"near"`: `list[(id_a, id_b, distance_m:int)]` — Facility 쌍, `NEAR_M` 이내, 각 시설당 가까운 20개까지, a<b로 1번만
  - `"along"`: `list[(facility_id, route_id, distance_m)]` — `ALONG_M` 이내
  - `"in_park"`: `list[(facility_id, park_id)]` — 비공원 시설이 공원 반경 `r=max(30, sqrt(PARK_AR/π))` m 안, 여러 개면 가장 가까운 1개
  - `"district"`: `dict[place_id, district_name]` — 점(선은 중심점)이 포함되는 동 경계(shapely); `districts: list[(name, shapely Polygon)]`는 `fetch_osm` 동 경계에서 만든다(`relations.load_districts(osm_data)`)
- [ ] **Step 1: 실패 테스트** — 450m 두 시설 near 포함, 550m 제외, 쌍 중복 없음; 경로에서 80m 벤치 along; 면적 31416㎡(r=100m) 공원 중심 90m 운동기구 in_park, 110m 아님; 사각 폴리곤 안 점 district.
- [ ] **Step 2–4:** FAIL → 구현(시설 수 ~1,700 → 격자 버킷 500m로 후보 축소) → PASS → commit `feat: relation computation`

### Task 6: 지식 DB 생성 + 웹 내보내기 + 예시 질의

**Files:** Create `pipeline/build_kg.py`, `pipeline/export_web.py`, `pipeline/run.py`, `kg/queries/near_park_exercise.rq`, `kg/queries/route_rest_facilities.rq`, `kg/queries/within_km.rq`; Test `tests/pipeline/test_kg.py`

**Interfaces:**
- Consumes: Task 2 스키마 IRI, Task 4/5 결과
- Produces:
  - `build_kg.build(places, rels) -> rdflib.Graph`; `build_kg.write(g, "kg/dongtan-data.ttl")`. 개체 IRI = `BASE + "id/{source}/{record_id}"`(source ∈ `std-{pk}`, `osm-{type}-{id}`, `geocode` 아님), 기하 노드 `…/geom`, Proximity 노드 `…/prox/{other_record}`. Dataset 개체 6+1개(OSM)에 이름·URL. 중심점 개체 `id/center`(`dt:Place`, label "청계동 552(지도 중심)").
  - `export_web.export(g, "site/data/places.geojson")` — SPARQL만 사용해 GeoJSON 생성. Feature.properties: `id, name, cls, cat`(`walk|run|bike|exercise|rest|park`), `d`(중심거리 km), `addr, src`(데이터셋명), `date, alt`(list), `info`(facilityInfo), `near`(list `{id,name,m}` 가까운 5개), `along`(경로 이름 목록 / 경로이면 시설 수), `park`(속한 공원명), `dong`. `meta`: `{center:[lat,lon], radiusKm:10, builtAt, counts}`.
  - `run.main(offline:bool)` — fetch→sources→merge→relations→build→export, 단계별 건수 출력.
- [ ] **Step 1: 실패 테스트** — 소형 고정 Place 3개+관계로 build → (a) 각 개체에 label·distanceFromCenterKm·fromDataset·asWKT 존재, (b) `near_park_exercise.rq`(공원 이름 바인딩 `"여울공원"`)가 450m 운동시설 반환, (c) export 결과 Feature 수 3, `cat` 매핑 맞음, `d` 2자리.
- [ ] **Step 2–4:** FAIL → 구현 → PASS
- [ ] **Step 5:** `python -m pipeline.run` 실제 실행 → 단계별 건수 기록, `kg/dongtan-data.ttl`·`site/data/places.geojson` 생성 확인 → commit `feat: knowledge graph build and web export`

### Task 7: 웹 로직 (순수 함수)

**Files:** Create `site/js/logic.js`; Test `tests/web/logic.test.mjs`

**Interfaces:**
- Produces (ES module exports):
  - `haversineKm([lat,lon],[lat,lon]) -> number`
  - `featureDistanceKm(origin, feature) -> number` (Point/LineString 최소거리)
  - `nextLocationMode(prevMode, userPos|null, center, {enterKm:10, exitKm:10.2}) -> "user"|"center"`
  - `rankFeatures(features, {origin, cats:Set, limit:50}) -> Array<{f, dUserKm|null}>` (origin 없으면 `d` 기준)
  - `formatDistance(km) -> "350m" | "1.2km"` (1km 미만 m 정수 10단위 반올림)
  - `naverLinks({name, lat, lon}) -> {app, web}`: `app = "nmap://route/walk?dlat={lat}&dlng={lon}&dname={enc(name)}&appname=io.github.romanryu_rgb.dongtan"`, `web = "https://map.naver.com/p/search/" + enc(name)`
- [ ] **Step 1: 실패 테스트** (`node --test tests/web`) — null 위치→center; 9.5km→user; user 상태에서 10.1km→user 유지, 10.3km→center; center 상태 10.1km→center; 0.35→"350m", 1.234→"1.2km"; 선 피처 거리 = 가장 가까운 점; cats 필터·limit 적용; naverLinks 인코딩.
- [ ] **Step 2–4:** FAIL → 구현 → PASS → commit `feat: web logic`

### Task 8: 지도 화면 (A안)

**Files:** Create `site/index.html`, `site/css/app.css`, `site/js/app.js`

**Interfaces:** Consumes `logic.js` 전부, `site/data/places.geojson`.

동작(모두 한국어):
- 전체화면 Leaflet, OSM 타일(`https://tile.openstreetmap.org/{z}/{x}/{y}.png`, 출처 표기 + 공공데이터 출처 정보 버튼), 초기 중심 `meta.center`, zoom 14, 10km 원(점선) 표시, 중심 🏁 마커.
- 상단 칩: 전체 / 🚶 / 🏃 / 🚲 / 💪 / 🪑 / 🌳(공원) — 아이콘만, `aria-label`·`title`에 한국어 이름, 다중 선택 토글(전체=모두).
- 경로 색: 산책 `#16a34a`, 런닝 `#f97316`, 자전거 `#2563eb`; 시설은 markercluster, 분류별 색 원형 아이콘.
- 하단 시트 3단(접힘 96px / 절반 45vh / 전체 85vh), 손잡이 드래그·탭으로 전환. 목록 = `rankFeatures` 상위 50: 이름(빈 이름이면 분류명), "나에게서 {formatDistance}"(user 모드만) · "중심 {d}km", 네이버 버튼(안드로이드: app 링크 시도 후 1.5초 내 페이지 유지 시 web; 그 외 web, 새 탭).
- 항목·마커 탭 → 시트에 상세: 분류, 주소, 동, 출처·기준일, 별칭, 공원보유시설, 속한 공원, 근처 시설 5개(탭하면 이동), 경로상 시설.
- 위치: `navigator.geolocation.watchPosition`(enableHighAccuracy, timeout 10000); 모드는 `nextLocationMode`; user 모드에서 파란 점 + "내 위치로" 버튼, center 모드면 숨기고 상단에 "현재 위치가 동탄 중심에서 10km 이상 떨어져 있어 중심 기준으로 보여 드립니다" / 위치 미확보 시 "위치를 확인할 수 없어 중심 기준으로 보여 드립니다" 한 번 토스트.
- PC(≥768px): 시트를 왼쪽 패널(폭 380px)로 표시.
- [ ] **Step 1:** 구현 후 로컬 서버 `python -m http.server 8000 -d site`
- [ ] **Step 2:** 브라우저 확인(모바일 375×812 + 데스크톱): 칩 토글로 레이어 변화, 시트 3단, 상세, 위치 거부 시 토스트·중심 정렬, 콘솔 에러 0 → commit `feat: map UI`

### Task 9: 배포 + 문서

**Files:** Create `.github/workflows/pages.yml`(actions/upload-pages-artifact@v3 path `site`, actions/deploy-pages@v4, push to main), `README.md`(목적, 실행법 `python -m pipeline.run`, 데이터 출처·라이선스, 온톨로지 개요, 예시 SPARQL, 생활편의시설 추가 방법: `sources.py` 매핑 1줄 + `Amenity` 하위 클래스 + `cat`/칩 추가)

- [ ] **Step 1:** **사용자 확인 후** `gh repo create romanryu-rgb/dongtan-walk-map --public --source . --push`, Pages 소스=Actions 설정(`gh api -X POST repos/romanryu-rgb/dongtan-walk-map/pages -f build_type=workflow`)
- [ ] **Step 2:** 워크플로 성공 확인 → `https://romanryu-rgb.github.io/dongtan-walk-map/` 200, `data/places.geojson` 로드 확인
- [ ] **Step 3:** 사용자 휴대폰 실기 확인 항목 전달(위치 권한, 네이버 앱 열림) → commit `docs: readme and pages deploy`
