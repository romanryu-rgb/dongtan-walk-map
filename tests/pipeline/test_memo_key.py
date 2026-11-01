import json

from pipeline.memo_key import make_key, verifier


def test_verifier_vector_matches_js():
    v = verifier("test-key-123", bytes.fromhex("00112233445566778899aabbccddeeff"), 1000)
    assert v == "9f8ab69a00ad2372eb209d64aae790fc689729d0ba2f7554e8a38a651b27172c"


def test_make_key_writes_secret_file_and_public_config(tmp_path):
    key_path, cfg_path = tmp_path / "secrets" / "memo-key.txt", tmp_path / "site" / "memo-config.json"
    key = make_key(key_path, cfg_path)
    assert len(key) >= 24 and key in key_path.read_text(encoding="utf-8")
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    assert set(cfg) == {"salt", "iterations", "verifier"}
    assert key not in cfg_path.read_text(encoding="utf-8")
    assert cfg["verifier"] == verifier(key, bytes.fromhex(cfg["salt"]), cfg["iterations"])


def test_make_key_refuses_to_overwrite_existing_key(tmp_path):
    key_path, cfg_path = tmp_path / "k.txt", tmp_path / "c.json"
    make_key(key_path, cfg_path)
    try:
        make_key(key_path, cfg_path)
    except FileExistsError:
        return
    raise AssertionError("existing key must not be overwritten")
