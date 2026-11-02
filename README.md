# 동탄 걷기·운동 지도

경기도 화성시 동탄구 청계동 552를 중심으로 반경 10km 안의 **산책로·런닝코스·자전거도로**와
그 주변 **휴게시설·운동시설·공원**을 보여 주는 휴대폰용 지도 사이트입니다.
모든 데이터는 **온톨로지(RDF/OWL) 기반 지식 DB** 하나에서 나오며, 나중에 MCP 서버로 AI 챗봇에 연결할 수 있게 설계했습니다.

- 사이트: https://romanryu-rgb.github.io/dongtan-walk-map/ · https://dongtan-walk-map.pages.dev/ (Cloudflare)
- 배포: `main`에 푸시하면 GitHub Pages(`pages.yml`)와 Cloudflare Pages(`cloudflare.yml`, 비밀값 `CLOUDFLARE_API_TOKEN` 필요)에 자동 배포
- 자동 갱신: 매주 월요일 03:00(KST) `refresh-data.yml`이 공공데이터·OSM을 새로 받아 다시 만들고, 바뀐 내용이 있을 때만 커밋·배포 (Actions 탭에서 수동 실행도 가능)
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
├─ 경로 dt:Route ── 산책로 dt:WalkingTrail / 런닝코스 dt:RunningCourse / 자전거도로 dt:BikePath / 등산로 dt:HikingTrail
├─ 산 정상 dt:Peak
└─ 시설 dt:Facility ── 휴게시설 dt:RestFacility / 운동시설 dt:ExerciseFacility / 공원 dt:Park
                     └─ 생활편의시설 dt:Amenity ── 화장실 dt:PublicToilet  (여기에 계속 추가)
```

모든 장소: `rdfs:label`(원본 이름), `skos:altLabel`(병합된 다른 이름), `dt:distanceFromCenterKm`,
`geo:hasGeometry/geo:asWKT`, `dt:fromDataset`, `dt:referenceDate`, `dt:sourceRecordId`.

관계: `dt:nearTo`(500m, 거리는 `dt:hasProximity → dt:Proximity{dt:proximityTarget, dt:distanceM}`),
`dt:alongRoute`/`dt:hasRouteFacility`(경로 100m 이내), `dt:locatedInPark`, `dt:inDistrict`.

예: "여울공원 근처 운동시설" → `kg/queries/near_park_exercise.rq` 에 `?parkName = "여울공원"@ko`.

## 데이터 출처

- 공공데이터포털 표준데이터: 전국도시공원정보, 전국실외운동기구설치정보, 전국그늘막쉼터, 전국무더위쉼터,
  전국자전거도로, 전국길관광정보, 전국공중화장실 (장소 이름은 원본 그대로 사용)
- 공공데이터포털 파일데이터(더 최신, 우선 적용): 경기도 화성시_무더위쉼터(2026-10-16, 화성시 안의 옛 표준데이터 대체),
  화성도시공사_공중화장실 설치현황(2025-12-31), 화성도시공사_화성시 공원 내 공중화장실 현황(2025-12-31, 좌표가 없어 해당 공원 상세에 표기)
- 모든 장소의 상세 화면에 출처·기준일을 표시하고, 기준일이 2년 넘은 자료는 ⚠️ 경고를 붙입니다(OSM은 수집일 표시)
- 행정안전부_공중화장실정보(LOCALDATA): 프로그램 다운로드가 막혀 있어 사람이 받은 CSV를 `data/manual/공중화장실정보_*.csv`로 넣으면
  화성시 화장실을 이 자료로 바꿉니다. 좌표가 없어 ① 2019년 표준데이터의 같은 이름 좌표 ② 도로명 주소 ③ 건물명 순으로
  키 없는 Photon/Nominatim(1초 1건, `data/cache/geocode.json`에 캐시)으로 위치를 찾고, 주소가 다른데 한 점에 몰린 결과는 뺍니다.
  기준일은 원본의 데이터갱신시점을 씁니다. 새 파일로 바꿔 넣으면 다음 주간 갱신 때 반영됩니다.
- OSM 원본은 `data/cache/osm/`에 마지막으로 잘 받은 자료를 보관하고, 주간 갱신 때 새로 받지 못하면 이 자료를 씁니다
- © OpenStreetMap contributors (ODbL): 운동기구·벤치·쉼터·런닝 트랙·산책로·자전거길·행정동 경계 보충
- 중심 좌표는 동탄순환대로22길(청계동 552 인근) 도로 중심점 근사값 — `pipeline/config.py` 의 `CENTER`

## 생활편의시설 추가 방법

화장실(`dt:PublicToilet`, 전국공중화장실표준데이터 pk `15012892`)이 첫 예시입니다. 같은 방법으로:

1. `ontology/dongtan.ttl` 에 `dt:Amenity` 하위 클래스 추가
2. `pipeline/sources.py` 의 `PUBLIC` 에 데이터셋 매핑 추가, `pipeline/records.py` 의 `FACILITY_CLASSES` 에 클래스 추가
3. `pipeline/export_web.py` 의 `CAT`, `site/js/app.js` 의 `CAT`, `site/index.html` 칩에 분류 추가
4. `python -m pipeline.run`

## 지도 도구

- **📏 거리 재기**: 버튼을 누르고 지도에서 출발 → 경유(여러 개) → 도착 순서로 누르면 구간별 거리·걷는 시간과 합계를 보여 줍니다.
  실제 걷는 길은 키가 필요 없는 공개 도보 경로 서버(routing.openstreetmap.de, OSRM)로 계산하고, 연결이 안 되면 직선거리(시속 4.5km)로 표시합니다.
- **📝 메모**: 암호 key를 아는 사람만 지도 위 지점에 메모를 남기고 볼 수 있습니다. 메모는 AES-GCM으로 암호화되어 **그 기기 브라우저에만** 저장되고,
  "파일로 내보내기/가져오기"로 다른 기기에 옮깁니다(같은 key 필요).
  - key 파일: `secrets/memo-key.txt` (이 PC에만 있음, git 제외). `#` 으로 시작하지 않는 첫 줄이 key입니다.
  - key 바꾸기: 파일의 key 줄을 고친 뒤 `python -m pipeline.memo_key --apply` 실행 → 커밋·푸시하면 1분 안에 사이트에 반영
  - 무작위 key 새로 만들기: 기존 파일을 지우고 `python -m pipeline.memo_key` 실행 후 배포
  - 사이트에는 key 대신 검증값(`site/data/memo-config.json`)만 공개됩니다. key를 바꾸면 이전 key로 저장한 메모는 열 수 없습니다.
- **❓ 사용법**: 오른쪽 ? 버튼으로 사용법 팝업을 엽니다. 처음 방문할 때 한 번 자동으로 열립니다(`site/js/help.js`, 내용을 크게 바꾸면 `HELP_VERSION`을 올리면 다시 한 번 자동으로 뜸).
- **반경 선택**: 1~10km. 내 위치가 동탄 10km 안이면 내 위치 기준, 아니면 지도 중심 기준입니다.
