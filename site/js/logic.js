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

// 출처·기준일 표시. 기준일이 2년 넘게 지나면 경고. OSM처럼 기준일이 없으면 수집일을 보여 준다.
export function sourceNote({ src, date }, today, collected = "") {
  if (!date) return { text: `${src} (수집일 ${collected || today}, 원본에 기준일 없음)`, stale: "" };
  const ageDays = (Date.parse(today) - Date.parse(date)) / 86400000;
  return { text: `${src} (기준일 ${date})`, stale: ageDays > 730 ? `⚠️ ${date.slice(0, 4)}년 자료라 실제와 다를 수 있습니다.` : "" };
}

// 카카오톡·네이버·인스타그램 등 앱 안 브라우저는 위치 권한을 막는 경우가 많다
export function isInAppBrowser(ua) {
  return /KAKAOTALK|NAVER\(inapp|Instagram|FBAN|FBAV|FB_IAB|Line\/|DaumApps|Whale\/.*inapp|; wv\)/i.test(ua);
}

// 안드로이드에서 같은 주소를 Chrome으로 여는 링크
export function chromeIntentUrl(href) {
  const u = new URL(href);
  return `intent://${u.host}${u.pathname}${u.search}#Intent;scheme=${u.protocol.replace(":", "")};package=com.android.chrome;end`;
}

// GeolocationPositionError.code → 사용자 안내
export function geoErrorMessage(code) {
  if (code === 1) return "위치 권한이 꺼져 있습니다. 주소창 왼쪽 아이콘 → 권한 → 위치를 '허용'으로 바꾼 뒤 새로고침해 주세요.";
  if (code === 2) return "휴대폰 위치(GPS)가 꺼져 있거나 신호를 못 잡았습니다. 빠른 설정에서 '위치'를 켜 주세요.";
  if (code === 3) return "위치를 찾는 중입니다… 실내라면 창가나 실외에서 더 빨리 잡힙니다.";
  return "위치를 확인할 수 없어 지도 중심(청계동 552) 기준으로 보여 드립니다.";
}
