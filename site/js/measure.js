// 시작·경유·도착 지점 사이 구간 거리. 실제 걷는 길은 OSRM(도보, 키 불필요), 실패 시 직선거리.
import { haversineKm } from "./logic.js";

export const WALK_KMH = 4.5;
const OSRM = "https://routing.openstreetmap.de/routed-foot/route/v1/foot/";

export function pointLabel(i, n) {
  if (i === 0) return "출발";
  if (i === n - 1) return "도착";
  return `경유${i}`;
}

export function osrmUrl(points) {
  return OSRM + points.map(([lat, lon]) => `${lon},${lat}`).join(";") + "?overview=full&geometries=geojson&steps=false";
}

const round2 = (x) => Math.round(x * 100) / 100;

// legs: OSRM route.legs([{distance(m), duration(s)}]) 또는 null(직선거리)
export function buildSegments(points, legs) {
  const segs = [];
  for (let i = 0; i < points.length - 1; i++) {
    const leg = legs && legs[i];
    const km = leg ? leg.distance / 1000 : haversineKm(points[i], points[i + 1]);
    const min = leg ? Math.round(leg.duration / 60) : Math.round((km / WALK_KMH) * 60);
    segs.push({ from: pointLabel(i, points.length), to: pointLabel(i + 1, points.length), km: round2(km), min, routed: !!leg });
  }
  segs.totalKm = round2(segs.reduce((a, s) => a + s.km, 0));
  segs.totalMin = segs.reduce((a, s) => a + s.min, 0);
  return segs;
}

export async function routeWalk(points, { timeoutMs = 8000 } = {}) {
  const ctl = new AbortController();
  const t = setTimeout(() => ctl.abort(), timeoutMs);
  try {
    const r = await fetch(osrmUrl(points), { signal: ctl.signal });
    const j = await r.json();
    if (j.code !== "Ok" || !j.routes?.length) return null;
    return { legs: j.routes[0].legs, line: j.routes[0].geometry.coordinates.map(([lon, lat]) => [lat, lon]) };
  } catch {
    return null;
  } finally {
    clearTimeout(t);
  }
}

export function formatDuration(min) {
  if (min < 60) return `${min}분`;
  const h = Math.floor(min / 60);
  const m = min % 60;
  return m ? `${h}시간 ${m}분` : `${h}시간`;
}
