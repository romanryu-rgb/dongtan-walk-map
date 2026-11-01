"""프로젝트 전역 설정. 중심 좌표는 이 파일 한 곳에서만 정의한다."""
from pathlib import Path

# 경기도 화성시 동탄구 청계동 552 (= 동탄순환대로22길 45, 동탄역모아미래도)
# OSM에 해당 번지가 없어 동탄순환대로22길 도로 중심점으로 근사함 (lat, lon)
CENTER = (37.19757, 127.11996)
CENTER_LABEL = "청계동 552(지도 중심)"
RADIUS_KM = 10.0

NEAR_M = 500       # 시설-시설 "근처" 기준
NEAR_MAX = 20      # 시설당 최대 근처 관계 수
ALONG_M = 100      # 시설이 경로 "위/옆"에 있다고 볼 거리
MERGE_M = 30       # 같은 분류 중복 병합 거리
BIKE_MATCH_M = 50  # 공공 자전거도로-OSM 선 매칭 거리

BASE = "https://romanryu-rgb.github.io/dongtan-walk-map/"
ONT = BASE + "ontology#"

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
KG_PATH = ROOT / "kg" / "dongtan-data.ttl"
ONTOLOGY_PATH = ROOT / "ontology" / "dongtan.ttl"
WEB_DATA_PATH = ROOT / "site" / "data" / "places.geojson"

USER_AGENT = "dongtan-walk-map/0.1 (github.com/romanryu-rgb)"
OVERPASS_URL = "https://overpass-api.de/api/interpreter"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
STD_HEADER_URL = "https://www.data.go.kr/download/columList.json?pk={pk}&ext=JSON"
STD_DATA_URL = "https://www.data.go.kr/download/standard.json"
