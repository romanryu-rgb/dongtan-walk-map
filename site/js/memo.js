// 암호 key로 잠그는 메모. key → PBKDF2(SHA-256) → AES-GCM 키. 사이트에는 검증값만 공개된다.
const enc = new TextEncoder();
const VERIFY_SUFFIX = enc.encode("dongtan-memo-verify");

const hex = (buf) => [...new Uint8Array(buf)].map((b) => b.toString(16).padStart(2, "0")).join("");
const fromHex = (h) => new Uint8Array(h.match(/../g).map((x) => parseInt(x, 16)));
const b64 = (u8) => btoa(String.fromCharCode(...u8));
const fromB64 = (s) => Uint8Array.from(atob(s), (c) => c.charCodeAt(0));

export async function deriveMemoKey(keyText, saltHex, iterations) {
  const base = await crypto.subtle.importKey("raw", enc.encode(keyText.trim()), "PBKDF2", false, ["deriveBits"]);
  const bits = new Uint8Array(await crypto.subtle.deriveBits(
    { name: "PBKDF2", hash: "SHA-256", salt: fromHex(saltHex), iterations }, base, 256));
  const joined = new Uint8Array(bits.length + VERIFY_SUFFIX.length);
  joined.set(bits);
  joined.set(VERIFY_SUFFIX, bits.length);
  const verifier = hex(await crypto.subtle.digest("SHA-256", joined));
  const aesKey = await crypto.subtle.importKey("raw", bits, "AES-GCM", false, ["encrypt", "decrypt"]);
  return { aesKey, verifier };
}

export async function encryptJSON(aesKey, value) {
  const iv = crypto.getRandomValues(new Uint8Array(12));
  const data = await crypto.subtle.encrypt({ name: "AES-GCM", iv }, aesKey, enc.encode(JSON.stringify(value)));
  return { v: 1, iv: b64(iv), data: b64(new Uint8Array(data)) };
}

export async function decryptJSON(aesKey, blob) {
  const plain = await crypto.subtle.decrypt({ name: "AES-GCM", iv: fromB64(blob.iv) }, aesKey, fromB64(blob.data));
  return JSON.parse(new TextDecoder().decode(plain));
}
