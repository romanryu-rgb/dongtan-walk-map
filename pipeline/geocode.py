"""키 없는 주소 → 좌표 변환. Photon(OSM 기반)을 먼저, 못 찾으면 Nominatim.
두 서비스의 사용 정책에 맞춰 1초에 1건씩 순서대로 부르고, 결과는 파일에 캐시한다(재실행 시 다시 부르지 않음).
결과: (lat, lon, precision, service) 또는 None. precision ∈ building | street | area
"""
import json
import time
import urllib.parse
import urllib.request

from . import config
from .geo import haversine_m

CACHE_PATH = config.ROOT / "data" / "cache" / "geocode.json"  # git에 포함해 매주 다시 부르지 않게 함
PHOTON_URL = "https://photon.komoot.io/api/"
MAX_FROM_CENTER_M = 15000  # 동명 주소로 다른 지역이 잡히는 것을 거름


def classify_photon(feature):
    t = feature["properties"].get("type")
    return "building" if t in ("house", "building") else "street" if t == "street" else "area"


def classify_nominatim(hit):
    t = hit.get("addresstype")
    if t in ("building", "house", "amenity", "shop", "tourism", "leisure"):
        return "building"
    if hit.get("class") == "highway" or t in ("road", "tertiary", "secondary", "primary", "residential"):
        return "street"
    return "area"


def _get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": config.USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


class AddressGeocoder:
    def __init__(self, cache_path=CACHE_PATH, delay=1.1):
        self.path = cache_path
        self.delay = delay
        self.cache = json.loads(cache_path.read_text(encoding="utf-8")) if cache_path.exists() else {}

    def _ok(self, lat, lon):
        return haversine_m(*config.CENTER, lat, lon) <= MAX_FROM_CENTER_M

    def _lookup(self, addr):
        time.sleep(self.delay)
        try:
            fs = _get_json(PHOTON_URL + "?" + urllib.parse.urlencode({"q": addr, "limit": 1, "lat": config.CENTER[0],
                                                                       "lon": config.CENTER[1]})).get("features", [])
            if fs:
                lon, lat = fs[0]["geometry"]["coordinates"]
                if self._ok(lat, lon) and classify_photon(fs[0]) != "area":
                    return [lat, lon, classify_photon(fs[0]), "photon"]
        except Exception:
            pass
        time.sleep(self.delay)
        try:
            hits = _get_json(config.NOMINATIM_URL + "?" + urllib.parse.urlencode(
                {"q": addr, "format": "json", "countrycodes": "kr", "limit": 1}))
            if hits:
                lat, lon = float(hits[0]["lat"]), float(hits[0]["lon"])
                if self._ok(lat, lon):
                    return [lat, lon, classify_nominatim(hits[0]), "nominatim"]
        except Exception:
            pass
        return None

    def __call__(self, addr):
        if addr not in self.cache:
            self.cache[addr] = self._lookup(addr)
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(self.cache, ensure_ascii=False, indent=0), encoding="utf-8")
        v = self.cache[addr]
        return tuple(v) if v else None
