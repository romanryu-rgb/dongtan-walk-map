import { test } from "node:test";
import assert from "node:assert/strict";
import {
  haversineKm, featureDistanceKm, nextLocationMode, rankFeatures, formatDistance, naverLinks,
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
