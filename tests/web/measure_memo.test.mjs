import { test } from "node:test";
import assert from "node:assert/strict";
import { osrmUrl, buildSegments, formatDuration, pointLabel } from "../../site/js/measure.js";
import { deriveMemoKey, encryptJSON, decryptJSON } from "../../site/js/memo.js";

const A = [37.2, 127.1];
const B = [37.21, 127.1];
const C = [37.21, 127.11];

test("point labels: start, waypoints, end", () => {
  assert.deepEqual([0, 1, 2, 3].map((i) => pointLabel(i, 4)), ["출발", "경유1", "경유2", "도착"]);
  assert.deepEqual([0, 1].map((i) => pointLabel(i, 2)), ["출발", "도착"]);
  assert.equal(pointLabel(0, 1), "출발");
});

test("osrm url uses lon,lat order and foot profile", () => {
  assert.equal(osrmUrl([A, B]),
    "https://routing.openstreetmap.de/routed-foot/route/v1/foot/127.1,37.2;127.1,37.21?overview=full&geometries=geojson&steps=false");
});

test("segments from routed legs", () => {
  const segs = buildSegments([A, B, C], [{ distance: 1200, duration: 900 }, { distance: 950, duration: 700 }]);
  assert.deepEqual(segs.map((s) => [s.from, s.to, s.km, s.routed]), [["출발", "경유1", 1.2, true], ["경유1", "도착", 0.95, true]]);
  assert.equal(segs.totalKm, 2.15);
  assert.equal(segs.totalMin, 27);
});

test("segments fall back to straight line at 4.5km/h when routing failed", () => {
  const segs = buildSegments([A, B], null);
  assert.equal(segs[0].routed, false);
  assert.ok(Math.abs(segs[0].km - 1.112) < 0.01);
  assert.equal(segs[0].min, Math.round((segs[0].km / 4.5) * 60));
});

test("formatDuration", () => {
  assert.equal(formatDuration(9), "9분");
  assert.equal(formatDuration(75), "1시간 15분");
  assert.equal(formatDuration(120), "2시간");
});

test("memo key verifier matches python pbkdf2 vector", async () => {
  const { verifier } = await deriveMemoKey("test-key-123", "00112233445566778899aabbccddeeff", 1000);
  assert.equal(verifier, "9f8ab69a00ad2372eb209d64aae790fc689729d0ba2f7554e8a38a651b27172c");
});

test("memo encrypt/decrypt round trip, wrong key fails", async () => {
  const good = await deriveMemoKey("test-key-123", "00112233445566778899aabbccddeeff", 1000);
  const bad = await deriveMemoKey("wrong", "00112233445566778899aabbccddeeff", 1000);
  const blob = await encryptJSON(good.aesKey, [{ lat: 37.2, lon: 127.1, text: "벤치 고장" }]);
  assert.ok(!JSON.stringify(blob).includes("벤치"));
  assert.deepEqual(await decryptJSON(good.aesKey, blob), [{ lat: 37.2, lon: 127.1, text: "벤치 고장" }]);
  await assert.rejects(decryptJSON(bad.aesKey, blob));
});
