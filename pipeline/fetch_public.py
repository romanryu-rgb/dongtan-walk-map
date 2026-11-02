"""공공데이터포털 표준데이터 다운로드 (키 없는 웹 다운로드 엔드포인트 사용)."""
import csv
import io
import json
import math
import re
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


def decode_csv(raw):
    """공공데이터 파일(CSV)은 UTF-8(BOM 포함) 또는 CP949. 헤더·값 앞뒤 공백 제거."""
    for enc in ("utf-8-sig", "cp949"):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise ValueError("알 수 없는 인코딩")
    rows = list(csv.reader(io.StringIO(text)))
    head = [h.strip() for h in rows[0]]
    return [{h: (v or "").strip() for h, v in zip(head, r)} for r in rows[1:] if any(c.strip() for c in r)]


def date_from_title(title):
    m = re.search(r"_(\d{4})(\d{2})(\d{2})\s*$", title.strip())
    return f"{m.group(1)}-{m.group(2)}-{m.group(3)}" if m else ""


def _get(url, data=None):
    req = urllib.request.Request(url, data=data, headers={"User-Agent": "Mozilla/5.0", "X-Requested-With": "XMLHttpRequest"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


def fetch_file(pk, refresh=False, sn=1):
    """공공데이터포털 '파일데이터'(fileData.do) 다운로드: 상세 페이지 → 파일 ID 조회 → 다운로드. 키 불필요."""
    path = config.RAW_DIR / f"file_{pk}_{sn}.json"
    if path.exists() and not refresh:
        return json.loads(path.read_text(encoding="utf-8"))
    page = _get(f"https://www.data.go.kr/data/{pk}/fileData.do").decode("utf-8")
    title = re.search(r"<title>(.*?)\|", page, re.S).group(1).strip()
    detail_pk = re.search(r'id="publicDataDetailPk"[^>]*value="([^"]+)"', page).group(1)
    info = json.loads(_get("https://www.data.go.kr/tcs/dss/selectFileDataDownload.do", urllib.parse.urlencode({
        "publicDataPk": pk, "publicDataDetailPk": detail_pk, "atchFileId": "", "fileDetailSn": sn,
        "publicDataTyCode": "PR0051"}).encode()))
    if not info.get("status"):
        raise RuntimeError(f"{pk} 파일 다운로드 정보를 찾지 못했습니다")
    raw = _get("https://www.data.go.kr/cmm/cmm/fileDownload.do?" + urllib.parse.urlencode(
        {"atchFileId": info["atchFileId"], "fileDetailSn": info["fileDetailSn"]}))
    data = {"title": title, "ref_date": date_from_title(title), "url": f"https://www.data.go.kr/data/{pk}/fileData.do",
            "rows": decode_csv(raw)}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return data


if __name__ == "__main__":
    from .sources import PUBLIC, TRAIL_PK
    for pk in [*PUBLIC, TRAIL_PK]:
        d = fetch_dataset(pk, refresh="--refresh" in sys.argv)
        print(pk, d["header"]["fileName"], len(d["rows"]))
