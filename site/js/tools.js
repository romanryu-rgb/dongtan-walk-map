// 지도 도구: 📏 거리 재기(출발·경유·도착) / 📝 암호 key 메모(이 기기에만 암호화 저장)
import { buildSegments, formatDuration, pointLabel, routeWalk } from "./measure.js";
import { decryptJSON, deriveMemoKey, encryptJSON } from "./memo.js";

const MEMO_STORE = "dongtan.memos.v1";

export function initTools({ map, $, esc, toast, showPanel, hidePanel }) {
  let tool = null; // "measure" | "memo" | null

  function setTool(t) {
    tool = t;
    $("#measure-btn").classList.toggle("active", t === "measure");
    $("#memo-btn").classList.toggle("active", t === "memo");
    map.getContainer().style.cursor = t ? "crosshair" : "";
    if (!t) hidePanel();
  }

  map.on("click", (e) => {
    const pt = [e.latlng.lat, e.latlng.lng];
    if (tool === "measure") addMeasurePoint(pt);
    else if (tool === "memo" && memo.key) openMemoForm({ lat: pt[0], lon: pt[1], text: "" });
  });

  // ── 📏 거리 재기 ───────────────────────────────
  const ms = { points: [], markers: [], line: null, seq: 0 };

  function clearMeasure() {
    ms.markers.forEach((m) => map.removeLayer(m));
    if (ms.line) map.removeLayer(ms.line);
    Object.assign(ms, { points: [], markers: [], line: null, seq: ms.seq + 1 });
  }

  function relabel() {
    ms.markers.forEach((m, i) => {
      const lab = pointLabel(i, ms.points.length);
      m.setIcon(L.divIcon({ className: "", html: `<div class="mpin" title="${lab}">${i === 0 ? "S" : i === ms.points.length - 1 && i > 0 ? "E" : i}</div>`, iconSize: [24, 24], iconAnchor: [12, 12] }));
    });
  }

  function addMeasurePoint(pt) {
    ms.points.push(pt);
    ms.markers.push(L.marker(pt, { interactive: false }).addTo(map));
    relabel();
    updateMeasure();
  }

  async function updateMeasure() {
    const seq = ++ms.seq;
    if (ms.line) { map.removeLayer(ms.line); ms.line = null; }
    if (ms.points.length < 2) { renderMeasure(null, false); return; }
    renderMeasure(null, true);
    const r = await routeWalk(ms.points);
    if (seq !== ms.seq) return; // 그 사이 점이 바뀜
    const segs = buildSegments(ms.points, r ? r.legs : null);
    ms.line = L.polyline(r ? r.line : ms.points, { color: "#0f766e", weight: 5, opacity: 0.85, dashArray: r ? null : "8 8" }).addTo(map);
    renderMeasure(segs, false);
  }

  function renderMeasure(segs, loading) {
    const n = ms.points.length;
    let body;
    if (n === 0) body = '<p class="hint">지도에서 <b>출발</b> 지점을 누르세요. 이어서 누르는 곳이 경유지가 되고, 마지막 점이 <b>도착</b>입니다.</p>';
    else if (n === 1) body = '<p class="hint">다음 지점(경유지 또는 도착)을 누르세요.</p>';
    else if (loading || !segs) body = '<p class="hint">실제 걷는 길로 거리를 계산하는 중…</p>';
    else {
      const rows = segs.map((s) => `<tr><td>${s.from} → ${s.to}</td><td class="num">${s.km.toFixed(2)}km</td><td class="num">${formatDuration(s.min)}</td></tr>`).join("");
      const straight = segs.some((s) => !s.routed) ? '<p class="hint">경로 서버에 연결하지 못해 <b>직선거리</b>로 표시했습니다(걷는 시간은 시속 4.5km 기준).</p>' : '<p class="hint">실제 걷는 길 기준(OpenStreetMap 도보 경로)입니다.</p>';
      body = `${straight}<table>${rows}<tr class="total"><td>합계</td><td class="num">${segs.totalKm.toFixed(2)}km</td><td class="num">${formatDuration(segs.totalMin)}</td></tr></table>`;
    }
    showPanel(`<h2>📏 거리 재기</h2>${body}
      <div class="row"><button class="btn" data-m="undo" ${n ? "" : "disabled"}>마지막 점 취소</button>
      <button class="btn" data-m="reset" ${n ? "" : "disabled"}>처음부터</button>
      <button class="btn primary" data-m="close">끝내기</button></div>`);
  }

  $("#measure-btn").addEventListener("click", () => {
    if (tool === "measure") { clearMeasure(); setTool(null); return; }
    setTool("measure");
    renderMeasure(null, false);
  });

  // ── 📝 메모 ────────────────────────────────────
  const memo = { key: null, items: [], markers: [], temp: null, cfg: null };

  async function loadConfig() {
    if (!memo.cfg) memo.cfg = await (await fetch("data/memo-config.json")).json();
    return memo.cfg;
  }

  function readStore() { try { return JSON.parse(localStorage.getItem(MEMO_STORE) || "null"); } catch { return null; } }

  async function saveStore() {
    const blob = await encryptJSON(memo.key, memo.items);
    try { localStorage.setItem(MEMO_STORE, JSON.stringify(blob)); return true; } catch {
      toast("이 브라우저에서는 메모를 저장할 수 없습니다(저장소 차단). 내보내기로 파일에 보관하세요.");
      return false;
    }
  }

  function drawMemoMarkers() {
    memo.markers.forEach((m) => map.removeLayer(m));
    memo.markers = memo.items.map((it) => L.marker([it.lat, it.lon], {
      icon: L.divIcon({ className: "", html: '<div class="memo-pin">📝</div>', iconSize: [24, 24], iconAnchor: [4, 22] }),
      title: it.text.slice(0, 40), zIndexOffset: 900,
    }).on("click", () => { if (tool !== "measure") { setTool("memo"); openMemoForm(it); } }).addTo(map));
  }

  function renderUnlock(err = "") {
    showPanel(`<h2>📝 메모 열기</h2>
      <p class="hint">메모는 암호 key를 아는 사람만 쓰고 볼 수 있습니다. 이 PC의 <b>secrets/memo-key.txt</b> 파일에 있는 key를 입력하세요.</p>
      <input id="memo-key" type="password" autocomplete="off" placeholder="암호 key" aria-label="암호 key">
      ${err ? `<div class="err">${esc(err)}</div>` : ""}
      <div class="row"><button class="btn primary" data-k="open">열기</button><button class="btn" data-k="close">닫기</button></div>`);
    $("#memo-key").focus();
  }

  async function unlock() {
    const keyText = $("#memo-key").value;
    if (!keyText.trim()) { renderUnlock("key를 입력하세요."); return; }
    const cfg = await loadConfig();
    const { aesKey, verifier } = await deriveMemoKey(keyText, cfg.salt, cfg.iterations);
    if (verifier !== cfg.verifier) { renderUnlock("key가 맞지 않습니다."); return; }
    memo.key = aesKey;
    const blob = readStore();
    memo.items = blob ? await decryptJSON(aesKey, blob).catch(() => []) : [];
    drawMemoMarkers();
    renderMemoHome();
  }

  function renderMemoHome() {
    const list = memo.items.length
      ? `<ul class="memos">${memo.items.slice().sort((a, b) => b.updated - a.updated).map((it) => `<li data-id="${esc(it.id)}">${esc(it.text.slice(0, 60))}<br><small>${new Date(it.updated).toLocaleString("ko-KR")}</small></li>`).join("")}</ul>`
      : '<p class="hint">아직 메모가 없습니다.</p>';
    showPanel(`<h2>📝 메모 (${memo.items.length})</h2>
      <p class="hint">지도에서 메모할 곳을 누르세요. 메모는 암호화되어 <b>이 기기에만</b> 저장됩니다.</p>${list}
      <div class="row"><button class="btn" data-k="export">파일로 내보내기</button>
      <button class="btn" data-k="import">파일 가져오기</button>
      <button class="btn" data-k="lock">잠그기</button><button class="btn primary" data-k="close">끝내기</button></div>
      <input id="memo-file" type="file" accept="application/json,.json" hidden>`);
  }

  function openMemoForm(it) {
    if (memo.temp) map.removeLayer(memo.temp);
    memo.temp = it.id ? null : L.marker([it.lat, it.lon], { interactive: false, opacity: 0.7 }).addTo(map);
    memo.editing = it;
    showPanel(`<h2>📝 ${it.id ? "메모 보기·수정" : "새 메모"}</h2>
      <p class="hint">위치 ${it.lat.toFixed(5)}, ${it.lon.toFixed(5)}</p>
      <textarea id="memo-text" maxlength="2000" aria-label="메모 내용">${esc(it.text)}</textarea>
      <div class="row"><button class="btn primary" data-k="save">저장</button>
      ${it.id ? '<button class="btn" data-k="delete">삭제</button>' : ""}
      <button class="btn" data-k="back">취소</button></div>`);
    if (!it.id) $("#memo-text").focus();
  }

  async function saveMemo() {
    const text = $("#memo-text").value.trim();
    if (!text) { toast("메모 내용을 입력하세요."); return; }
    const it = memo.editing;
    if (it.id) Object.assign(it, { text, updated: Date.now() });
    else memo.items.push({ id: crypto.randomUUID(), lat: it.lat, lon: it.lon, text, created: Date.now(), updated: Date.now() });
    if (await saveStore()) toast("메모를 저장했습니다.");
    backToMemoHome();
  }

  function backToMemoHome() {
    if (memo.temp) { map.removeLayer(memo.temp); memo.temp = null; }
    drawMemoMarkers();
    renderMemoHome();
  }

  async function exportMemos() {
    const blob = await encryptJSON(memo.key, memo.items);
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([JSON.stringify(blob)], { type: "application/json" }));
    a.download = `dongtan-memos-${new Date().toISOString().slice(0, 10)}.json`;
    a.click();
    URL.revokeObjectURL(a.href);
  }

  async function importMemos(file) {
    try {
      const items = await decryptJSON(memo.key, JSON.parse(await file.text()));
      const byId = new Map(memo.items.map((x) => [x.id, x]));
      for (const x of items) if (!byId.has(x.id) || byId.get(x.id).updated < x.updated) byId.set(x.id, x);
      memo.items = [...byId.values()];
      await saveStore();
      toast(`메모 ${items.length}개를 가져왔습니다.`);
      backToMemoHome();
    } catch {
      toast("가져오지 못했습니다. 같은 암호 key로 만든 메모 파일인지 확인하세요.");
    }
  }

  function lockMemos() {
    memo.key = null;
    memo.items = [];
    drawMemoMarkers();
    setTool(null);
  }

  $("#memo-btn").addEventListener("click", () => {
    if (tool === "memo") { setTool(null); return; }
    if (tool === "measure") clearMeasure();
    setTool("memo");
    if (memo.key) renderMemoHome(); else renderUnlock();
  });

  $("#tool").addEventListener("click", async (e) => {
    const m = e.target.closest("[data-m]")?.dataset.m;
    if (m === "undo") { ms.points.pop(); map.removeLayer(ms.markers.pop()); relabel(); updateMeasure(); }
    if (m === "reset") { clearMeasure(); renderMeasure(null, false); }
    if (m === "close") { clearMeasure(); setTool(null); }
    const k = e.target.closest("[data-k]")?.dataset.k;
    if (k === "open") await unlock();
    if (k === "close") { if (memo.temp) { map.removeLayer(memo.temp); memo.temp = null; } setTool(null); }
    if (k === "save") await saveMemo();
    if (k === "back") backToMemoHome();
    if (k === "delete") { memo.items = memo.items.filter((x) => x !== memo.editing); await saveStore(); backToMemoHome(); }
    if (k === "export") await exportMemos();
    if (k === "import") $("#memo-file").click();
    if (k === "lock") lockMemos();
    const li = e.target.closest("ul.memos li[data-id]");
    if (li) {
      const it = memo.items.find((x) => x.id === li.dataset.id);
      if (it) { map.setView([it.lat, it.lon], Math.max(map.getZoom(), 17)); openMemoForm(it); }
    }
  });
  $("#tool").addEventListener("change", (e) => { if (e.target.id === "memo-file" && e.target.files[0]) importMemos(e.target.files[0]); });
  $("#tool").addEventListener("keydown", (e) => { if (e.target.id === "memo-key" && e.key === "Enter") unlock(); });

  // 장소 마커 클릭과 겹치지 않도록: 도구 사용 중엔 상세 대신 도구 동작
  return { activeTool: () => tool };
}
