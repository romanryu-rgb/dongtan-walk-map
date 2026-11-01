"""OpenStreetMap Overpass 질의 + Nominatim 지오코딩 (키 불필요, 결과 캐시)."""
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

from . import config

_A = "around:{r},{lat},{lon}".format(r=int(config.RADIUS_KM * 1000), lat=config.CENTER[0], lon=config.CENTER[1])

QUERIES = {
    "fitness": f'nwr({_A})[leisure=fitness_station];out center tags;',
    "rest": f'(node({_A})[amenity=bench];node({_A})[amenity=shelter];node({_A})[leisure=picnic_table];);out body;',
    "running": f'(way({_A})[leisure=track][sport~"running|athletics"];relation({_A})[route=running];);out geom;',
    "walking": f'(relation({_A})[route=foot];way({_A})[highway=footway][name];);out geom;',
    # 산길(highway=path)은 모두 여기서 받고, 이름·포장 여부로 등산로/산책로를 나눈다(sources.osm_places)
    "hiking": f'(relation({_A})[route=hiking];way({_A})[highway=path][bicycle!=designated];);out geom;',
    "peaks": f'node({_A})[natural=peak][name];out body;',
    "cycleway": f'(way({_A})[highway=cycleway];way({_A})[bicycle=designated][highway~"^(path|footway)$"];);out tags geom;',
    "districts": f'relation({_A})[boundary=administrative][admin_level=8];out geom;',
}


def query(name, ql=None, refresh=False):
    path = config.RAW_DIR / f"osm_{name}.json"
    if path.exists() and not refresh:
        return json.loads(path.read_text(encoding="utf-8"))
    body = urllib.parse.urlencode({"data": "[out:json][timeout:180];" + (ql or QUERIES[name])}).encode()
    for attempt in range(6):
        url = config.OVERPASS_URLS[attempt % len(config.OVERPASS_URLS)]
        try:
            req = urllib.request.Request(url, data=body, headers={"User-Agent": config.USER_AGENT})
            with urllib.request.urlopen(req, timeout=240) as r:
                data = json.loads(r.read().decode("utf-8"))
            break
        except urllib.error.HTTPError as e:
            if e.code not in (429, 502, 503, 504) or attempt == 5:
                raise
            time.sleep(10)
        except (TimeoutError, urllib.error.URLError):
            if attempt == 5:
                raise
            time.sleep(10)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return data


class Geocoder:
    """Nominatim, 1초 간격, 파일 캐시. 결과 없음도 캐시한다."""

    def __init__(self):
        self.path = config.RAW_DIR / "geocode.json"
        self.cache = json.loads(self.path.read_text(encoding="utf-8")) if self.path.exists() else {}

    def __call__(self, addr):
        if addr not in self.cache:
            q = urllib.parse.urlencode({"q": addr, "format": "json", "countrycodes": "kr", "limit": 1})
            req = urllib.request.Request(config.NOMINATIM_URL + "?" + q, headers={"User-Agent": config.USER_AGENT})
            time.sleep(1.1)
            with urllib.request.urlopen(req, timeout=60) as r:
                res = json.loads(r.read().decode("utf-8"))
            self.cache[addr] = [float(res[0]["lat"]), float(res[0]["lon"])] if res else None
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(self.cache, ensure_ascii=False), encoding="utf-8")
        v = self.cache[addr]
        return tuple(v) if v else None


if __name__ == "__main__":
    for n in QUERIES:
        d = query(n, refresh="--refresh" in sys.argv)
        print(n, len(d["elements"]))
