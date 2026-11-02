"""주간 갱신용: 새로 만든 웹 데이터가 이전과 실제로 다른지(빌드 날짜만 바뀐 건 제외) 판단한다.

python -m pipeline.changed OLD.geojson NEW.geojson  → 바뀌었으면 종료코드 0, 같으면 1
"""
import json
import sys


def _strip(path):
    d = json.loads(path.read_text(encoding="utf-8"))
    d.get("meta", {}).pop("builtAt", None)
    return d


def data_changed(old_path, new_path):
    if not old_path.exists():
        return True
    return _strip(old_path) != _strip(new_path)


if __name__ == "__main__":
    from pathlib import Path
    sys.exit(0 if data_changed(Path(sys.argv[1]), Path(sys.argv[2])) else 1)
