import { clampRadius, featureDistanceKm, formatDistance, haversineKm, naverLinks, nextLocationMode, rankFeatures } from "./logic.js";
import { initTools } from "./tools.js";
import { initHelp } from "./help.js";

const CAT = {
  walk: { label: "산책로", icon: "🚶", color: "#16a34a" },
  run: { label: "런닝코스", icon: "🏃", color: "#f97316" },
  bike: { label: "자전거도로", icon: "🚲", color: "#2563eb" },
  hike: { label: "등산로", icon: "⛰️", color: "#92400e" },
  exercise: { label: "운동시설", icon: "💪", color: "#dc2626" },
  rest: { label: "휴게시설", icon: "🪑", color: "#7c3aed" },
  park: { label: "공원", icon: "🌳", color: "#15803d" },
  toilet: { label: "화장실", icon: "🚻", color: "#0e7490" },
  conv: { label: "편의점", icon: "🏪", color: "#db2777" },
};
const ALL = new Set(Object.keys(CAT));
const LIST_LIMIT = 50;
const IS_ANDROID = /Android/i.test(navigator.userAgent);

const $ = (s) => document.querySelector(s);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const displayName = (p) => p.name || (p.type ? `${p.type} (${CAT[p.cat].label})` : `이름 없는 ${CAT[p.cat].label}`);
const latlonOf = (f) => {
  const g = f.geometry;
  const c = g.type === "Point" ? g.coordinates : g.coordinates[Math.floor(g.coordinates.length / 2)];
  return [c[1], c[0]];
};

const RADIUS_KEY = "dongtan.radiusKm";
const savedRadius = () => { try { return localStorage.getItem(RADIUS_KEY); } catch { return null; } };
const state = {
  cats: new Set(ALL), mode: "center", userPos: null, features: [], byId: new Map(), layers: {}, layerOf: new Map(),
  center: null, toastShown: "", radiusKm: clampRadius(savedRadius()), radiusCircle: null, lastRefPos: null,
};

// ── 지도 ──────────────────────────────────────────
const map = L.map("map", { zoomControl: false, preferCanvas: true });
L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
  maxZoom: 19, attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
}).addTo(map);
map.attributionControl.setPrefix(false);
let meMarker = null;

function pinIcon(cat) {
  const c = CAT[cat];
  return L.divIcon({ className: "", html: `<div class="pin" style="background:${c.color}">${c.icon}</div>`, iconSize: [22, 22], iconAnchor: [11, 11] });
}

function buildLayers() {
  for (const cat of Object.keys(CAT)) {
    state.layers[cat] = ["walk", "run", "bike", "hike"].includes(cat)
      ? L.layerGroup()
      : L.markerClusterGroup({ showCoverageOnHover: false, maxClusterRadius: 45, disableClusteringAtZoom: 17 });
  }
  for (const f of state.features) {
    const p = f.properties;
    const c = CAT[p.cat];
    let layer;
    if (f.geometry.type === "LineString") {
      const style = p.cat === "bike" ? { weight: 2.5, opacity: 0.55 }
        : p.cat === "hike" ? { weight: 3.5, opacity: 0.8, dashArray: "6 5" } : { weight: 5, opacity: 0.85 };
      layer = L.polyline(f.geometry.coordinates.map(([lon, lat]) => [lat, lon]), { color: c.color, ...style });
    } else if (["walk", "run", "bike", "hike"].includes(p.cat)) {
      layer = L.marker(latlonOf(f), { icon: pinIcon(p.cat), title: displayName(p) }); // 시작점만 있는 경로
    } else {
      layer = L.marker(latlonOf(f), { icon: pinIcon(p.cat), title: displayName(p) });
    }
    layer.on("click", () => showDetail(p.id));
    state.layerOf.set(p.id, layer);
  }
  applyLayers();
  refreshMap();
}

// 반경 기준점: 내 위치 모드면 내 위치, 아니면 지도 중심
function refPos() { return origin() || state.center; }

function refreshMap() {
  const visible = rankFeatures(state.features, { origin: origin(), limit: Infinity, radiusKm: state.radiusKm });
  for (const layer of Object.values(state.layers)) layer.clearLayers();
  for (const { f } of visible) state.layers[f.properties.cat].addLayer(state.layerOf.get(f.properties.id));
  const ref = refPos();
  state.lastRefPos = ref;
  if (!state.radiusCircle) {
    state.radiusCircle = L.circle(ref, { radius: 1, color: "#0f766e", weight: 2, fillColor: "#14b8a6", fillOpacity: 0.05, interactive: false }).addTo(map);
  }
  state.radiusCircle.setLatLng(ref).setRadius(state.radiusKm * 1000);
}

function setRadius(km, { fit = true } = {}) {
  state.radiusKm = clampRadius(km);
  try { localStorage.setItem(RADIUS_KEY, String(state.radiusKm)); } catch { /* 저장 불가 환경 */ }
  $("#radius").value = String(state.radiusKm);
  refreshMap();
  renderList();
  if (fit) map.fitBounds(state.radiusCircle.getBounds(), { padding: [20, 20] });
}

function applyLayers() {
  for (const [cat, layer] of Object.entries(state.layers)) {
    if (state.cats.has(cat)) layer.addTo(map); else map.removeLayer(layer);
  }
}

// ── 목록 ──────────────────────────────────────────
function origin() { return state.mode === "user" ? state.userPos : null; }

function renderList() {
  const opts = { origin: origin(), cats: state.cats, skipUnnamedRoutes: true, radiusKm: state.radiusKm };
  const ranked = rankFeatures(state.features, { ...opts, limit: LIST_LIMIT });
  $("#list-title").textContent = state.mode === "user" ? `내 주변 ${state.radiusKm}km · 가까운 순` : `중심 ${state.radiusKm}km · 가까운 순`;
  const total = rankFeatures(state.features, { ...opts, limit: Infinity }).length;
  $("#list-count").textContent = total > LIST_LIMIT ? `${LIST_LIMIT} / ${total}곳` : `${total}곳`;
  $("#list").innerHTML = ranked.map(({ f, dUserKm }) => {
    const p = f.properties;
    const c = CAT[p.cat];
    const mine = dUserKm != null ? `나에게서 ${formatDistance(dUserKm)} · ` : "";
    return `<li data-id="${esc(p.id)}">
      <span class="dot" style="background:${c.color}22">${c.icon}</span>
      <div class="li-body"><div class="li-name">${p.h24 ? '<span class="badge">24시간</span> ' : ""}${esc(displayName(p))}</div>
        <div class="li-dist">${mine}중심 ${p.d.toFixed(2)}km</div></div>
      <button class="naver" data-nav="${esc(p.id)}" aria-label="네이버 지도에서 열기">네이버</button></li>`;
  }).join("");
}

$("#list").addEventListener("click", (e) => {
  const nav = e.target.closest("[data-nav]");
  if (nav) { e.stopPropagation(); openNaver(nav.dataset.nav); return; }
  const li = e.target.closest("li[data-id]");
  if (li) showDetail(li.dataset.id);
});

function openNaver(id) {
  const f = state.byId.get(id);
  const p = f.properties;
  const [lat, lon] = latlonOf(f);
  const links = naverLinks({ name: p.name || p.addr || displayName(p), lat, lon });
  if (IS_ANDROID) {
    const t = setTimeout(() => { if (!document.hidden) window.location.href = links.web; }, 1500);
    document.addEventListener("visibilitychange", () => clearTimeout(t), { once: true });
    window.location.href = links.app;
  } else {
    window.open(links.web, "_blank", "noopener");
  }
}

// ── 상세 ──────────────────────────────────────────
function relList(items, withM) {
  if (!items.length) return "";
  return `<ul class="rel">${items.map((r) => {
    const c = CAT[r.cat] || { icon: "•" };
    const nm = r.name || (CAT[r.cat] ? `이름 없는 ${CAT[r.cat].label}` : "");
    return `<li>${c.icon} <a href="#" data-go="${esc(r.id)}">${esc(nm)}</a>${withM ? ` · ${r.m}m` : ""}</li>`;
  }).join("")}</ul>`;
}

function showDetail(id) {
  const f = state.byId.get(id);
  if (!f) return;
  const p = f.properties;
  const c = CAT[p.cat];
  const dUser = origin() ? `나에게서 ${formatDistance(featureDistanceKm(origin(), f))} · ` : "";
  const rows = [
    ["분류", `${c.icon} ${c.label}${p.type ? ` · ${esc(p.type)}` : ""}`],
    ["거리", `${dUser}중심 ${p.d.toFixed(2)}km`],
    p.len ? ["길이", `${p.len}km`] : null,
    p.addr ? ["주소", esc(p.addr)] : null,
    p.dong ? ["행정동", esc(p.dong)] : null,
    p.park ? ["속한 공원", esc(p.park)] : null,
    p.alt.length ? ["다른 이름", esc(p.alt.join(", "))] : null,
    p.info ? ["시설 정보", esc(p.info)] : null,
    p.along.length ? ["지나는 길", esc(p.along.join(", "))] : null,
    p.near.length ? ["근처 시설", relList(p.near, true)] : null,
    p.fac.length ? ["경로상 시설", relList(p.fac.slice(0, 15), true)] : null,
    ["출처", `${esc(p.src)}${p.date ? ` (${esc(p.date)})` : ""}`],
  ].filter(Boolean);
  $("#detail").innerHTML = `<button class="back" data-back>‹ 목록으로</button>
    <h2>${esc(displayName(p))}</h2>
    <button class="naver" data-nav="${esc(p.id)}">네이버 지도에서 길찾기</button>
    <dl>${rows.map(([k, v]) => `<dt>${k}</dt><dd>${v}</dd>`).join("")}</dl>`;
  $("#list").hidden = true;
  $("#sheet-head").hidden = true;
  $("#detail").hidden = false;
  $("#detail").scrollTop = 0;
  setSheet("half");
  if (f.geometry.type === "LineString") {
    map.fitBounds(L.latLngBounds(f.geometry.coordinates.map(([lon, lat]) => [lat, lon])), { padding: [40, 40], maxZoom: 17 });
  } else {
    map.setView(latlonOf(f), Math.max(map.getZoom(), 17));
  }
}

$("#detail").addEventListener("click", (e) => {
  if (e.target.closest("[data-back]")) { $("#detail").hidden = true; $("#list").hidden = false; $("#sheet-head").hidden = false; return; }
  const nav = e.target.closest("[data-nav]");
  if (nav) { openNaver(nav.dataset.nav); return; }
  const go = e.target.closest("[data-go]");
  if (go) { e.preventDefault(); showDetail(go.dataset.go); }
});

// ── 도구 패널(거리 재기·메모) ─────────────────────
function showPanel(html) {
  $("#tool").innerHTML = html;
  ["#list", "#detail", "#sheet-head"].forEach((s) => { $(s).hidden = true; });
  $("#tool").hidden = false;
  if (sheetState() === "peek") setSheet("half");
}
function hidePanel() {
  $("#tool").hidden = true;
  $("#tool").innerHTML = "";
  $("#list").hidden = false;
  $("#sheet-head").hidden = false;
}

// ── 분류 칩 ───────────────────────────────────────
$("#chips").addEventListener("click", (e) => {
  const b = e.target.closest(".chip");
  if (!b) return;
  const cat = b.dataset.cat;
  if (cat === "all") state.cats = new Set(ALL);
  else if (state.cats.size === ALL.size) state.cats = new Set([cat]);
  else if (state.cats.has(cat)) { state.cats.delete(cat); if (!state.cats.size) state.cats = new Set(ALL); }
  else state.cats.add(cat);
  document.querySelectorAll(".chip").forEach((el) => {
    const on = el.dataset.cat === "all" ? state.cats.size === ALL.size : state.cats.size !== ALL.size && state.cats.has(el.dataset.cat);
    el.classList.toggle("on", on);
    el.setAttribute("aria-pressed", on);
  });
  applyLayers();
  renderList();
});

// ── 하단 시트 ─────────────────────────────────────
const SHEETS = ["peek", "half", "full"];
function setSheet(s) { const el = $("#sheet"); SHEETS.forEach((x) => el.classList.toggle(x, x === s)); }
function sheetState() { return SHEETS.find((s) => $("#sheet").classList.contains(s)); }
let dragY = null;
$("#grip").addEventListener("pointerdown", (e) => { dragY = e.clientY; $("#grip").setPointerCapture(e.pointerId); });
$("#grip").addEventListener("pointerup", (e) => {
  if (dragY == null) return;
  const dy = e.clientY - dragY;
  dragY = null;
  const i = SHEETS.indexOf(sheetState());
  if (Math.abs(dy) < 10) setSheet(SHEETS[(i + 1) % 3]);
  else setSheet(SHEETS[Math.max(0, Math.min(2, i + (dy < 0 ? 1 : -1)))]);
});
$("#grip").addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); setSheet(SHEETS[(SHEETS.indexOf(sheetState()) + 1) % 3]); } });

// ── 위치 ──────────────────────────────────────────
function toast(msg) {
  if (state.toastShown === msg) return;
  state.toastShown = msg;
  const t = $("#toast");
  t.textContent = msg;
  t.hidden = false;
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => { t.hidden = true; }, 5000);
}

function updateMode(pos) {
  const prev = state.mode;
  state.userPos = pos;
  state.mode = nextLocationMode(prev, pos, state.center);
  if (state.mode === "user") {
    if (!meMarker) meMarker = L.marker(pos, { icon: L.divIcon({ className: "", html: '<div class="me"></div>', iconSize: [18, 18], iconAnchor: [9, 9] }), interactive: false, zIndexOffset: 1000 });
    meMarker.setLatLng(pos).addTo(map);
    $("#locate").hidden = false;
    if (prev !== "user") { map.setView(pos, 16); state.toastShown = ""; }
  } else {
    if (meMarker) map.removeLayer(meMarker);
    $("#locate").hidden = true;
    if (pos) toast("현재 위치가 동탄 중심에서 10km 이상 떨어져 있어 중심 기준으로 보여 드립니다.");
    else toast("위치를 확인할 수 없어 지도 중심(청계동 552) 기준으로 보여 드립니다.");
  }
  const moved = state.lastRefPos && haversineKm(state.lastRefPos, refPos()) > 0.1;
  if (prev !== state.mode || moved) refreshMap(); // 100m 넘게 움직였을 때만 지도 다시 거르기
  if (prev !== state.mode || state.mode === "user") renderList();
}

function startGeolocation() {
  if (!("geolocation" in navigator)) { updateMode(null); return; }
  // 권한 창에 응답하지 않으면 콜백이 오지 않으므로 12초 뒤 중심 기준 안내
  setTimeout(() => { if (!state.userPos) updateMode(null); }, 12000);
  navigator.geolocation.watchPosition(
    (p) => updateMode([p.coords.latitude, p.coords.longitude]),
    () => { if (state.mode !== "user") updateMode(null); },
    { enableHighAccuracy: true, timeout: 10000, maximumAge: 15000 },
  );
}

$("#locate").addEventListener("click", () => { if (state.userPos) map.setView(state.userPos, 17); });
$("#home").addEventListener("click", () => map.setView(state.center, 14));

// ── 시작 ──────────────────────────────────────────
async function main() {
  const fc = await (await fetch("data/places.geojson")).json();
  state.center = fc.meta.center;
  state.features = fc.features;
  state.features.forEach((f) => state.byId.set(f.properties.id, f));
  $("#built").textContent = `데이터 기준 ${fc.meta.builtAt}`;
  map.setView(state.center, 14);
  L.circle(state.center, { radius: fc.meta.radiusKm * 1000, color: "#64748b", weight: 1.5, dashArray: "6 6", fill: false, interactive: false }).addTo(map);
  L.marker(state.center, { icon: L.divIcon({ className: "", html: '<div class="center-pin">🏁</div>', iconSize: [24, 24], iconAnchor: [4, 22] }), title: fc.meta.centerLabel }).addTo(map);
  $("#radius").value = String(state.radiusKm);
  $("#radius").addEventListener("change", (e) => setRadius(e.target.value));
  buildLayers();
  renderList();
  startGeolocation();
  initTools({ map, $, esc, toast, setSheet, showPanel, hidePanel });
  initHelp($);
}

main().catch((err) => {
  console.error(err);
  toast("데이터를 불러오지 못했습니다. 잠시 후 다시 시도해 주세요.");
});
