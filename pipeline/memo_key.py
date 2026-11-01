"""메모용 암호 key 만들기: python -m pipeline.memo_key

- 비밀 key → secrets/memo-key.txt (이 PC에만, git에 올라가지 않음)
- 공개 검증값(salt, iterations, verifier) → site/data/memo-config.json
  verifier = SHA-256(PBKDF2-SHA256(key, salt, iterations, 32바이트) + "dongtan-memo-verify")
  사이트(site/js/memo.js)가 같은 방식으로 입력한 key를 확인한다.
"""
import hashlib
import json
import secrets

from . import config

KEY_PATH = config.ROOT / "secrets" / "memo-key.txt"
CFG_PATH = config.ROOT / "site" / "data" / "memo-config.json"
ITERATIONS = 200_000


def verifier(key, salt, iterations):
    bits = hashlib.pbkdf2_hmac("sha256", key.strip().encode("utf-8"), salt, iterations, 32)
    return hashlib.sha256(bits + b"dongtan-memo-verify").hexdigest()


def _write_config(key, cfg_path, iterations):
    salt = secrets.token_bytes(16)
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    cfg_path.write_text(json.dumps({"salt": salt.hex(), "iterations": iterations,
                                    "verifier": verifier(key, salt, iterations)}, indent=2), encoding="utf-8")


def read_key(key_path=KEY_PATH):
    """key 파일에서 '#'으로 시작하지 않는 첫 줄을 key로 읽는다."""
    for line in key_path.read_text(encoding="utf-8").splitlines():
        if line.strip() and not line.lstrip().startswith("#"):
            return line.strip()
    raise ValueError(f"key 파일에 key가 없습니다: {key_path}")


def apply_key(key_path=KEY_PATH, cfg_path=CFG_PATH, iterations=ITERATIONS):
    """직접 고친 key 파일로 공개 검증값을 다시 만든다(배포해야 사이트에 반영)."""
    _write_config(read_key(key_path), cfg_path, iterations)


def make_key(key_path=KEY_PATH, cfg_path=CFG_PATH, iterations=ITERATIONS):
    if key_path.exists():
        raise FileExistsError(f"이미 key 파일이 있습니다: {key_path} (바꾸려면 직접 지운 뒤 다시 실행)")
    key = secrets.token_urlsafe(18)  # 24자
    key_path.parent.mkdir(parents=True, exist_ok=True)
    key_path.write_text(
        "# 동탄 걷기 지도 메모 암호 key — 이 key를 아는 사람만 메모를 쓰고 볼 수 있습니다.\n"
        "# 다른 사람에게 보내지 마세요. 잃어버리면 이 key로 저장한 메모는 다시 열 수 없습니다.\n"
        f"{key}\n", encoding="utf-8")
    _write_config(key, cfg_path, iterations)
    return key


if __name__ == "__main__":
    import sys
    if "--apply" in sys.argv:
        apply_key()
        print(f"key 파일의 값으로 검증값을 다시 만들었습니다: {CFG_PATH} (배포하면 사이트에 반영)")
    else:
        make_key()
        print(f"key 파일을 만들었습니다: {KEY_PATH}")
