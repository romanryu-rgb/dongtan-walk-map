"""공공데이터포털 표준데이터 다운로드 (키 없는 웹 다운로드 엔드포인트 사용)."""
import json
import math
import sys
import urllib.parse
import urllib.request

from . import config


def _get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "X-Requested-With": "XMLHttpRequest"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read().decode("utf-8"))


def fetch_dataset(pk, refresh=False):
    path = config.RAW_DIR / f"std_{pk}.json"
    if path.exists() and not refresh:
        return json.loads(path.read_text(encoding="utf-8"))
    header = _get_json(config.STD_HEADER_URL.format(pk=pk))
    tv, total = header["tableVO"], header["totalCount"]
    rows = []
    for page in range(1, math.ceil(total / 10000) + 1):  # 페이지는 1부터
        q = [("colNmList", c) for c in tv["colNmList"]] + [
            ("totalCount", total), ("svcTableNm", tv["svcTableNm"]), ("perPage", 10000), ("page", page)]
        rows += _get_json(config.STD_DATA_URL + "?publicDataPk=" + pk + "&" + urllib.parse.urlencode(q))
    data = {"header": header, "rows": rows}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return data


if __name__ == "__main__":
    from .sources import PUBLIC, TRAIL_PK
    for pk in [*PUBLIC, TRAIL_PK]:
        d = fetch_dataset(pk, refresh="--refresh" in sys.argv)
        print(pk, d["header"]["fileName"], len(d["rows"]))
