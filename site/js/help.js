// 사용법 도움말 팝업. 처음 방문(또는 도움말 내용이 바뀐 뒤 첫 방문) 때 한 번 자동으로 열린다.
export const HELP_VERSION = 1;
const SEEN_KEY = "dongtan.helpSeen";

export const HELP_SECTIONS = [
  {
    title: "🗺️ 지도 보기",
    body: `<p>지도 중심은 🏁 <b>청계동 552</b>입니다. 점선 원은 이 지도가 다루는 <b>10km</b> 범위입니다.</p>
      <p>위치 권한을 허용하면 내 위치가 <b>파란 점</b>으로 보이고, 목록이 "내 주변 가까운 순"으로 바뀝니다.
      동탄 중심에서 10km 넘게 떨어져 있거나 PC처럼 위치를 알 수 없으면, 내 위치 없이 중심 기준으로 보여 드립니다.</p>`,
  },
  {
    title: "📍 조회 반경",
    body: `<p>왼쪽 위 <b>반경</b> 버튼(예: 3km)에서 1~10km를 고르면 그 안의 장소만 지도와 목록에 나옵니다.
      기준은 내 위치(동탄 10km 안일 때) 또는 지도 중심입니다. 고른 값은 이 기기에 기억됩니다.</p>`,
  },
  {
    title: "🔘 분류 버튼",
    body: `<p>위쪽 아이콘을 누르면 그 분류만 봅니다. 여러 개를 함께 켤 수 있고, <b>전체</b>를 누르면 모두 보입니다.</p>
      <ul class="help-cats">
        <li>🚶 산책로</li><li>🏃 런닝코스</li><li>🚲 자전거도로</li><li>⛰️ 등산로·산 정상</li>
        <li>💪 운동시설</li><li>🪑 휴게시설(그늘막·쉼터·벤치)</li><li>🌳 공원</li><li>🚻 화장실</li>
        <li>🏪 편의점 (<span class="badge">24시간</span> 표시는 24시간 영업이 확인된 곳)</li>
      </ul>`,
  },
  {
    title: "📋 목록과 상세 정보",
    body: `<p>아래 목록 손잡이를 위로 끌거나 누르면 목록이 펼쳐집니다. 장소를 누르면 주소, 행정동, 시설 정보, 근처 시설, 출처가 나옵니다.</p>
      <p><b>네이버</b> 버튼을 누르면 네이버 지도 앱에서 걸어가는 길을 찾아 줍니다(앱이 없으면 네이버 지도 웹으로 열림).</p>`,
  },
  {
    title: "📏 거리 재기",
    body: `<p>📏 버튼을 누른 뒤 지도에서 <b>출발 → 경유지(여러 개) → 도착</b> 순서로 누르세요.
      구간마다 실제 걷는 길 기준 거리와 걷는 시간, 합계가 나옵니다. 경로 서버가 응답하지 않으면 직선거리로 대신 보여 드립니다.</p>
      <p>"마지막 점 취소", "처음부터", "끝내기"로 고칠 수 있습니다.</p>`,
  },
  {
    title: "📝 메모",
    body: `<p>📝 버튼을 누르고 <b>암호 key</b>를 입력하면, 지도에서 누른 곳에 메모를 남기고 고치거나 지울 수 있습니다.
      key를 아는 사람만 쓰고 볼 수 있습니다.</p>
      <p>메모는 암호화되어 <b>지금 쓰는 기기에만</b> 저장됩니다. 다른 기기로 옮길 때는 "파일로 내보내기 → 가져오기"를 쓰세요(같은 key 필요).</p>`,
  },
  {
    title: "◎ 🏁 위치 버튼",
    body: `<p>◎ 는 내 위치로, 🏁 는 지도 중심(청계동 552)으로 지도를 옮깁니다.</p>`,
  },
  {
    title: "📱 위치가 안 보일 때 (삼성 휴대폰)",
    body: `<p>휴대폰 <b>설정 → 위치</b>를 켜고, 브라우저(삼성 인터넷·크롬)의 사이트 권한에서 이 사이트의 위치를 <b>허용</b>으로 바꾼 뒤 새로고침하세요.</p>`,
  },
  {
    title: "ℹ️ 데이터",
    body: `<p>공공데이터포털 표준데이터(공원·운동기구·그늘막·무더위쉼터·자전거도로·공중화장실)와 OpenStreetMap 데이터를 씁니다.
      장소 이름은 원본 그대로이며, 실제와 다를 수 있습니다.</p>`,
  },
];

export function shouldShowHelpOnStart(seenValue) {
  return Number(seenValue) !== HELP_VERSION;
}

export function initHelp($) {
  const dlg = $("#help");
  $("#help-body").innerHTML = HELP_SECTIONS.map((s) => `<section><h3>${s.title}</h3>${s.body}</section>`).join("");
  const open = () => { dlg.showModal(); $("#help-body").scrollTop = 0; };
  const close = () => {
    dlg.close();
    try { localStorage.setItem(SEEN_KEY, String(HELP_VERSION)); } catch { /* 저장 불가 환경 */ }
  };
  $("#help-btn").addEventListener("click", open);
  $("#help-close").addEventListener("click", close);
  $("#help-ok").addEventListener("click", close);
  dlg.addEventListener("cancel", (e) => { e.preventDefault(); close(); });
  dlg.addEventListener("click", (e) => { if (e.target === dlg) close(); }); // 바깥 누르면 닫기
  let seen = null;
  try { seen = localStorage.getItem(SEEN_KEY); } catch { /* 저장 불가 환경 */ }
  if (shouldShowHelpOnStart(seen)) open();
}
