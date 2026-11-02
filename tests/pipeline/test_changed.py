import json

from pipeline.changed import data_changed


def _write(path, built, feats):
    path.write_text(json.dumps({"type": "FeatureCollection", "meta": {"builtAt": built, "counts": {}}, "features": feats},
                               ensure_ascii=False), encoding="utf-8")


def test_only_build_date_differs_is_not_a_change(tmp_path):
    a, b = tmp_path / "a.json", tmp_path / "b.json"
    _write(a, "2026-11-01", [{"properties": {"id": "x"}}])
    _write(b, "2026-11-08", [{"properties": {"id": "x"}}])
    assert data_changed(a, b) is False


def test_feature_difference_is_a_change(tmp_path):
    a, b = tmp_path / "a.json", tmp_path / "b.json"
    _write(a, "2026-11-01", [{"properties": {"id": "x"}}])
    _write(b, "2026-11-08", [{"properties": {"id": "y"}}])
    assert data_changed(a, b) is True


def test_missing_old_file_is_a_change(tmp_path):
    b = tmp_path / "b.json"
    _write(b, "2026-11-08", [])
    assert data_changed(tmp_path / "none.json", b) is True
