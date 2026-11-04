import { test } from "node:test";
import assert from "node:assert/strict";
import {
  haversineKm, featureDistanceKm, nextLocationMode, rankFeatures, formatDistance, naverLinks, clampRadius,
  isInAppBrowser, chromeIntentUrl, geoErrorMessage,
} from "../../site/js/logic.js";

const C = [37.19757, 127.11996];
const KM_LAT = 1 / 111.19508;
const north = (km) => [C[0] + km * KM_LAT, C[1]];

const pt = (id, cat, d, latlon) => ({
  type: "Feature", geometry: { type: "Point", coordinates: [latlon[1], latlon[0]] }, properties: { id, cat, d },
});

test("haversineKm about 1km north", () => {
  assert.ok(Math.abs(haversineKm(C, north(1)) - 1) < 0.005);
});

test("no position falls back to center", () => {
  assert.equal(nextLocationMode("user", null, C), "center");
  assert.equal(nextLocationMode(null, null, C), "center");
});

test("inside 10km uses user position", () => {
  assert.equal(nextLocationMode("center", north(9.5), C), "user");
});

test("hysteresis: user stays user at 10.1km, leaves at 10.3km", () => {
  assert.equal(nextLocationMode("user", north(10.1), C), "user");
  assert.equal(nextLocationMode("user", north(10.3), C), "center");
});

test("center stays center at 10.1km", () => {
  assert.equal(nextLocationMode("center", north(10.1), C), "center");
});

test("formatDistance", () => {
  assert.equal(formatDistance(0.35), "350m");
  assert.equal(formatDistance(0.004), "0m");
  assert.equal(formatDistance(0.996), "1.0km");
  assert.equal(formatDistance(1.234), "1.2km");
});

test("line feature distance uses nearest point on line", () => {
  const f = { type: "Feature", properties: {}, geometry: { type: "LineString",
    coordinates: [[C[1] - 0.01, C[0] + 2 * KM_LAT], [C[1] + 0.01, C[0] + 2 * KM_LAT]] } };
  assert.ok(Math.abs(featureDistanceKm(C, f) - 2) < 0.01);
});

test("rankFeatures filters by category, sorts by user distance, limits", () => {
  const fs = [pt("a", "rest", 5, north(5)), pt("b", "rest", 1, north(1)), pt("c", "park", 0.5, north(0.5)),
    pt("d", "rest", 3, north(3))];
  const r = rankFeatures(fs, { origin: north(4.9), cats: new Set(["rest"]), limit: 2 });
  assert.deepEqual(r.map((x) => x.f.properties.id), ["a", "d"]);
  assert.ok(r[0].dUserKm < 0.2);
});

test("rankFeatures without origin sorts by center distance and has null user distance", () => {
  const fs = [pt("a", "rest", 5, north(5)), pt("b", "rest", 1, north(1))];
  const r = rankFeatures(fs, { origin: null, cats: new Set(["rest"]), limit: 50 });
  assert.deepEqual(r.map((x) => x.f.properties.id), ["b", "a"]);
  assert.equal(r[0].dUserKm, null);
});

test("naverLinks encodes name", () => {
  const l = naverLinks({ name: "여울 공원", lat: 37.2, lon: 127.1 });
  assert.equal(l.app, "nmap://route/walk?dlat=37.2&dlng=127.1&dname=%EC%97%AC%EC%9A%B8%20%EA%B3%B5%EC%9B%90&appname=io.github.romanryu_rgb.dongtan");
  assert.equal(l.web, "https://map.naver.com/p/search/%EC%97%AC%EC%9A%B8%20%EA%B3%B5%EC%9B%90");
});

test("rankFeatures can skip unnamed routes for the list", () => {
  const line = (id, name) => ({ type: "Feature", properties: { id, cat: "bike", d: 1, name },
    geometry: { type: "LineString", coordinates: [[C[1], C[0]], [C[1] + 0.001, C[0]]] } });
  const fs = [line("u", ""), line("n", "동탄대로L"), { ...pt("b", "rest", 0.1, north(0.1)), properties: { id: "b", cat: "rest", d: 0.1, name: "" } }];
  const r = rankFeatures(fs, { origin: null, cats: new Set(["bike", "rest"]), limit: 50, skipUnnamedRoutes: true });
  assert.deepEqual(r.map((x) => x.f.properties.id).sort(), ["b", "n"]);
});

test("rankFeatures radius around user position", () => {
  const fs = [pt("a", "rest", 5, north(5)), pt("b", "rest", 3, north(3)), pt("c", "rest", 1, north(1))];
  const r = rankFeatures(fs, { origin: north(4.5), cats: new Set(["rest"]), limit: 50, radiusKm: 1 });
  assert.deepEqual(r.map((x) => x.f.properties.id), ["a"]);
});

test("rankFeatures radius around center uses center distance when no position", () => {
  const fs = [pt("a", "rest", 5, north(5)), pt("b", "rest", 2.9, north(2.9)), pt("c", "rest", 1, north(1))];
  const r = rankFeatures(fs, { origin: null, cats: new Set(["rest"]), limit: 50, radiusKm: 3 });
  assert.deepEqual(r.map((x) => x.f.properties.id), ["c", "b"]);
});

test("clampRadius keeps 1..10 whole km and defaults to 3", () => {
  assert.equal(clampRadius("5"), 5);
  assert.equal(clampRadius(0), 1);
  assert.equal(clampRadius(42), 10);
  assert.equal(clampRadius("abc"), 3);
  assert.equal(clampRadius(null), 3);
});

test("unnamed hiking trails are skipped from the list too", () => {
  const f = { type: "Feature", properties: { id: "h", cat: "hike", d: 1, name: "" },
    geometry: { type: "LineString", coordinates: [[C[1], C[0]], [C[1] + 0.001, C[0]]] } };
  assert.equal(rankFeatures([f], { cats: new Set(["hike"]), skipUnnamedRoutes: true }).length, 0);
});

test("sourceNote shows date and warns when older than 2 years", async () => {
  const { sourceNote } = await import("../../site/js/logic.js");
  assert.deepEqual(sourceNote({ src: "전국공중화장실표준데이터", date: "2019-04-03" }, "2026-11-02"),
    { text: "전국공중화장실표준데이터 (기준일 2019-04-03)", stale: "⚠️ 2019년 자료라 실제와 다를 수 있습니다." });
  assert.deepEqual(sourceNote({ src: "경기도 화성시_무더위쉼터", date: "2026-10-16" }, "2026-11-02"),
    { text: "경기도 화성시_무더위쉼터 (기준일 2026-10-16)", stale: "" });
  assert.deepEqual(sourceNote({ src: "OpenStreetMap", date: "" }, "2026-11-02", "2026-11-02"),
    { text: "OpenStreetMap (수집일 2026-11-02, 원본에 기준일 없음)", stale: "" });
});

test("in-app browsers are detected, normal browsers are not", () => {
  assert.equal(isInAppBrowser("Mozilla/5.0 (Linux; Android 14; SM-S918N) AppleWebKit/537.36 Chrome/130 Mobile Safari/537.36 KAKAOTALK 10.8.0"), true);
  assert.equal(isInAppBrowser("Mozilla/5.0 (Linux; Android 14; SM-S918N; wv) AppleWebKit/537.36 Version/4.0 Chrome/130 Mobile Safari/537.36 NAVER(inapp; search; 2000; 12.6.1)"), true);
  assert.equal(isInAppBrowser("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Instagram 300.0"), true);
  assert.equal(isInAppBrowser("Mozilla/5.0 (Linux; Android 14; SM-S918N) AppleWebKit/537.36 Chrome/130 Mobile Safari/537.36"), false);
  assert.equal(isInAppBrowser("Mozilla/5.0 (Linux; Android 14; SM-S918N) AppleWebKit/537.36 SamsungBrowser/26.0 Chrome/122 Mobile Safari/537.36"), false);
  assert.equal(isInAppBrowser("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Version/17.0 Mobile/15E148 Safari/604.1"), false);
});

test("chrome intent url keeps path and query", () => {
  assert.equal(chromeIntentUrl("https://example.pages.dev/a/?debug=1"),
    "intent://example.pages.dev/a/?debug=1#Intent;scheme=https;package=com.android.chrome;end");
});

test("geolocation error codes map to specific advice", () => {
  assert.match(geoErrorMessage(1), /권한/);
  assert.match(geoErrorMessage(2), /GPS/);
  assert.match(geoErrorMessage(3), /찾는 중/);
  assert.match(geoErrorMessage(99), /확인할 수 없어/);
});
