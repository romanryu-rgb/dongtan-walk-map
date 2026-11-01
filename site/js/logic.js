// 지도 화면의 순수 계산 함수. 좌표 인자는 [lat, lon], GeoJSON 좌표는 [lon, lat].

const R_KM = 6371.0088;
const rad = (d) => (d * Math.PI) / 180;

export function haversineKm(a, b) {
  const h = Math.sin(rad(b[0] - a[0]) / 2) ** 2
    + Math.cos(rad(a[0])) * Math.cos(rad(b[0])) * Math.sin(rad(b[1] - a[1]) / 2) ** 2;
  return 2 * R_KM * Math.asin(Math.sqrt(h));
}

function project([lat, lon], lat0) {
  return [rad(lon) * R_KM * Math.cos(rad(lat0)), rad(lat) * R_KM];
}

function pointSegmentKm(p, a, b) {
  const [px, py] = project(p, p[0]);
  const [ax, ay] = project(a, p[0]);
  const [bx, by] = project(b, p[0]);
  const dx = bx - ax;
  const dy = by - ay;
  const len2 = dx * dx + dy * dy;
  const t = len2 === 0 ? 0 : Math.max(0, Math.min(1, ((px - ax) * dx + (py - ay) * dy) / len2));
  return Math.hypot(px - (ax + t * dx), py - (ay + t * dy));
}

export function featureDistanceKm(origin, feature) {
  const g = feature.geometry;
  if (g.type === "Point") return haversineKm(origin, [g.coordinates[1], g.coordinates[0]]);
  const pts = g.coordinates.map(([lon, lat]) => [lat, lon]);
  if (pts.length === 1) return haversineKm(origin, pts[0]);
  let best = Infinity;
  for (let i = 0; i < pts.length - 1; i++) best = Math.min(best, pointSegmentKm(origin, pts[i], pts[i + 1]));
  return best;
}

// 10km 경계에서 깜빡이지 않도록: 들어올 때 < enterKm, 나갈 때 >= exitKm
export function nextLocationMode(prevMode, userPos, center, { enterKm = 10, exitKm = 10.2 } = {}) {
  if (!userPos) return "center";
  const d = haversineKm(userPos, center);
  if (prevMode === "user") return d >= exitKm ? "center" : "user";
  return d < enterKm ? "user" : "center";
}

const ROUTE_CATS = new Set(["walk", "run", "bike", "hike"]);

// 반경 기준점: 내 위치가 있으면 내 위치, 없으면 지도 중심(properties.d = 중심 거리)
export function rankFeatures(features, { origin = null, cats, limit = 50, skipUnnamedRoutes = false, radiusKm = Infinity }) {
  const out = [];
  for (const f of features) {
    if (cats && !cats.has(f.properties.cat)) continue;
    if (skipUnnamedRoutes && !f.properties.name && ROUTE_CATS.has(f.properties.cat)) continue;
    const dUserKm = origin ? featureDistanceKm(origin, f) : null;
    if ((origin ? dUserKm : f.properties.d) > radiusKm) continue;
    out.push({ f, dUserKm });
  }
  out.sort((a, b) => (origin ? a.dUserKm - b.dUserKm : a.f.properties.d - b.f.properties.d));
  return out.slice(0, limit);
}

export function formatDistance(km) {
  if (km < 1 && Math.round(km * 100) < 100) return `${Math.round(km * 100) * 10}m`;
  return `${km.toFixed(1)}km`;
}

export function naverLinks({ name, lat, lon }) {
  const n = encodeURIComponent(name);
  return {
    app: `nmap://route/walk?dlat=${lat}&dlng=${lon}&dname=${n}&appname=io.github.romanryu_rgb.dongtan`,
    web: `https://map.naver.com/p/search/${n}`,
  };
}

export const RADIUS_DEFAULT_KM = 3;

export function clampRadius(v) {
  const n = Math.round(Number(v));
  if (v === null || v === undefined || Number.isNaN(n)) return RADIUS_DEFAULT_KM;
  return Math.min(10, Math.max(1, n));
}
