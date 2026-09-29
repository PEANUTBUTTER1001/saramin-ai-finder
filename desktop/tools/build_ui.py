"""Copy the approved visual prototype into the desktop UI shell.

The generated page keeps the prototype CSS and layout. Its sample-data scripts are
replaced with the real QWebChannel client in app.js.
"""

import re
from pathlib import Path

root = Path(__file__).resolve().parents[2]
source = (root / "outputs" / "saramin-desktop-prototype.html").read_text(encoding="utf-8")
page = source.split("  <script>", 1)[0]
page = page.replace("Saramin AI Finder — PC 앱 프로토타입", "Saramin Finder — PC 공고 관리")
page = page.replace("</style>", """
    .analysis-layout{display:grid;grid-template-columns:minmax(0,1fr) 280px;gap:18px}
    .analysis-row{padding:16px 18px;border-bottom:1px solid var(--line)}
    .analysis-row:last-child{border:0}
    .analysis-row strong{display:block;font-size:13px;color:#263b56}
    .analysis-row small{display:block;color:var(--muted);margin:5px 0}
    .analysis-row p{white-space:pre-wrap;line-height:1.6;font-size:12px;margin:10px 0;color:#43536b}
    .analysis-actions{display:flex;flex-wrap:wrap;align-items:center;gap:4px 12px}
    .analysis-stat{padding:12px 16px;border:0;border-bottom:1px solid var(--line);display:flex;justify-content:space-between;width:100%;background:#fff;cursor:pointer;text-align:left}
    .analysis-stat:hover{background:#f5f8fe}
    .alert-actions{display:flex;flex-wrap:wrap;justify-content:flex-end;align-items:center;gap:4px 8px}
    .profile-regions{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:5px;max-height:165px;overflow:auto;border:1px solid var(--line);border-radius:8px;padding:8px;margin:7px 0 16px}
    .profile-check{display:flex;align-items:center;gap:7px;font-size:11px;color:#43536a;cursor:pointer;padding:4px}
    .profile-check input{width:auto!important;height:auto!important;margin:0;accent-color:var(--blue)}
    .profile-check:has(input:disabled){opacity:.5}
    .profile-summary{font-size:12px;color:#4c6685;margin-bottom:18px}
    .crawl-criteria{border-top:1px solid var(--line);padding-top:14px;margin-top:14px}
    .crawl-criteria .profile-regions{max-height:125px}
    .data-table{min-width:920px}
    .run-events-button,.run-event-link{display:block;background:none;border:0;color:#9dc7ff;text-align:left;padding:3px 0;font:inherit}
    .run-events-button{text-decoration:underline;margin:4px 0;cursor:pointer}
    .run-event-link{padding-left:12px;cursor:pointer}
    .run-event-link:hover{text-decoration:underline}
    .run-event-group{padding:4px 0;border-top:1px solid #31425d}
    .run-event-group strong{color:#dbe7f8}
    .multi-filter{position:relative;min-width:0}
    .multi-filter summary{list-style:none;min-height:37px;border:1px solid #dce3ed;border-radius:8px;background:#fff;padding:9px 10px;color:#334359;font-size:11px;cursor:pointer;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
    .multi-filter summary::-webkit-details-marker{display:none}
    .multi-filter summary:focus-visible{outline:3px solid #8aa9ff}
    .multi-filter[open] summary{border-color:#82a0ed}
    .multi-options{position:absolute;z-index:12;top:39px;left:0;min-width:100%;width:max(230px,100%);max-width:min(340px,85vw);background:#fff;border:1px solid #dce3ed;border-radius:9px;box-shadow:0 14px 30px #17253f26;padding:7px}
    .multi-options-list{max-height:230px;overflow:auto}
    .multi-option{display:flex;align-items:center;gap:8px;padding:6px 5px;font-size:11px;cursor:pointer;white-space:normal}
    .multi-option input{width:auto;height:auto;margin:0;accent-color:var(--blue)}
    .multi-clear{width:100%;border:0;background:#edf3ff;color:#365dc7;border-radius:6px;padding:7px;font-size:11px;text-align:left}
    .settings-card{max-width:650px;padding:24px}
    .settings-range{width:100%;accent-color:var(--blue);margin:18px 0}
    .settings-value{font-size:20px;font-weight:700}
    .settings-note{color:var(--muted);line-height:1.6}
    [hidden]{display:none!important}
    @media(max-width:1350px){.explore-grid{grid-template-columns:minmax(0,1fr)}}
    @media(max-width:900px){.analysis-layout{grid-template-columns:1fr}}
  </style>""")
page = page.replace('<span class="demo-pill">샘플 데이터 · 프로토타입</span>',
                    '<span class="demo-pill">실제 로컬 데이터</span>')
page = page.replace('PC 로컬 저장 구상', 'PC 로컬 누적 저장')
page = page.replace('로컬 데이터 설계', '로컬 데이터 보관')
page = page.replace('상세 텍스트 분석 예시', '섹션별 기술 키워드')
page = page.replace('프로토타입에서 확인할 수 있는 동작', '실제 앱에서 적용하는 동작')
page = page.replace('샘플 데이터 준비됨', '수집 대기 중')
page = page.replace('2026.09.28 09:41', '—')
page = page.replace('무엇을 저장하나요?', '무엇을 저장하나요?')
page = page.replace('목록 값과 상세 텍스트, 수집 이력을 함께 기록해 조건별 조회가 가능하도록 설계합니다.',
                    '목록 값과 상세 텍스트, 자격요건·우대사항, 수집 이력을 로컬에 저장합니다.')
page = page.replace('<div class="notice"><strong>화면 시연</strong><span>이 파일은 실제 사람인에 연결하지 않습니다. 수집과 저장은 샘플 데이터로 동작을 보여줍니다.</span></div>',
                    '<div class="notice"><strong>로컬 보관</strong><span>공고 목록과 읽을 수 있는 상세 텍스트를 이 PC에 누적 저장합니다.</span></div>')
page = page.replace('<button class="nav-btn" data-view="watch">',
                    '<button class="nav-btn" data-view="analysis"><svg class="nav-icon"><use href="#i-search"/></svg><span>요건 분석</span></button>\n        <button class="nav-btn" data-view="watch">', 1)
page = page.replace('<button data-view="watch"><svg>',
                    '<button data-view="analysis"><svg><use href="#i-search"/></svg>요건 분석</button><button data-view="watch"><svg>', 1)
analysis = """
        <section class="view" id="view-analysis" aria-label="요건 분석" hidden>
          <div class="page-head"><div><p class="eyebrow">Requirement Analysis</p><h1>자격요건 · 우대사항 분석</h1><p class="lead">두 섹션을 분리해 검색하고, 기술 키워드가 포함된 공고 수를 비교합니다.</p></div><button class="btn primary" id="exportAnalysis">CSV 내보내기</button></div>
          <div class="card filter-card"><div class="filter-grid"><div class="field"><label for="analysisKind">분석 섹션</label><select id="analysisKind"><option value="qualification">자격요건</option><option value="preference">우대사항</option></select></div><div class="field"><label for="analysisText">섹션 문장 검색</label><input id="analysisText" type="search" placeholder="예: Python"></div><div class="field"><label for="analysisCompany">회사</label><select id="analysisCompany"><option value="">전체 회사</option></select></div><div class="field"><label for="analysisSector">직무 분야</label><select id="analysisSector"><option value="">전체 분야</option></select></div><div class="field"><label for="analysisCareer">경력</label><select id="analysisCareer"><option value="">전체 경력</option></select></div><div class="field"><label for="analysisTech">기술 키워드</label><select id="analysisTech"><option value="">전체 기술</option></select></div><div class="field"><label for="analysisQuery">수집 검색어</label><select id="analysisQuery"><option value="">전체 검색어</option></select></div><div class="field"><label for="analysisDate">최근 수집일</label><input id="analysisDate" type="date"></div></div></div>
          <div class="analysis-layout"><div class="card"><div class="card-head"><div><h2>분리 저장된 원문 <span id="analysisCount">0</span>건</h2><p>추출에 성공한 섹션만 정확한 통계에 포함합니다.</p></div></div><div id="analysisRows"></div><div class="table-footer"><button class="btn small" id="analysisPrev">이전</button><span id="analysisPage">1</span><button class="btn small" id="analysisNext">다음</button></div></div><aside class="card"><div class="card-head"><div><h2>기술 키워드별 공고 수</h2><p>선택한 섹션에서 발견된 서로 다른 공고 기준</p></div></div><div id="analysisKeywords"></div></aside></div>
        </section>
"""
page = page.replace('        <section class="view" id="view-watch"',
                    analysis + '        <section class="view" id="view-watch"', 1)
profile_card = """
              <div class="card"><div class="card-head"><div><h2>공통 검색 조건</h2><p>AI를 포함한 모든 감시 검색어에 적용됩니다.</p></div></div>
                <form class="watch-form" id="profileForm" novalidate>
                  <div class="field"><label>근무 지역</label><label class="profile-check"><input id="profileNationwide" type="checkbox">지역 제한 없음</label><div class="profile-regions" id="profileRegions"></div></div>
                  <div class="field"><label for="profileExperience">경력</label><select id="profileExperience"><option value="both">신입 + 경력</option><option value="new">신입만</option><option value="career">경력만</option><option value="any">경력 제한 없음</option></select></div>
                  <div class="field" id="profileMaxField"><label for="profileCareerMax">최대 경력 · 년 (비우면 제한 없음)</label><input id="profileCareerMax" type="number" min="0" max="30" step="1" placeholder="제한 없음"></div>
                  <div class="field"><label for="profileEducation">학력</label><select id="profileEducation"><option value="both">학력무관 + 4년제 대졸 이상</option><option value="none">학력무관만</option><option value="university">4년제 대졸 이상만</option><option value="any">학력 제한 없음</option></select></div>
                  <button class="btn primary" type="submit" id="saveProfile" style="width:100%">검색 조건 저장</button>
                  <p class="watch-error" id="profileError" role="alert"></p><p class="watch-help">조건을 변경하면 기존 감시의 기준 목록을 새 조건으로 다시 만듭니다. 저장된 공고와 알림은 유지됩니다.</p>
                </form></div>
"""
page = page.replace('            <div class="watch-stack">\n              <div class="card">',
                    '            <div class="watch-stack">\n' + profile_card + '              <div class="card">', 1)
page = page.replace('          <div class="watch-layout">',
                    '          <div class="notice profile-summary" id="profileSummary">검색 조건을 불러오는 중입니다.</div>\n          <div class="watch-layout">', 1)
page = page.replace('>샘플 수집 시작</button>', '>실제 수집 시작</button>')
page = page.replace('현재 Android 앱의 검색 조건을 기본값으로 반영', '감시 공통 검색 조건을 기본값으로 불러옵니다.')
manual_criteria = """<div class="field crawl-criteria"><label>이번 수집 검색 조건</label><p class="form-note">감시 조건을 기본값으로 불러오며, 여기서 바꿔도 감시 설정은 바뀌지 않습니다.</p><button class="btn small" type="button" id="resetCrawlCriteria">감시 조건 다시 불러오기</button>
  <div class="field"><label>근무 지역</label><label class="profile-check"><input id="crawlNationwide" type="checkbox">지역 제한 없음</label><div class="profile-regions" id="crawlRegions"></div></div>
  <div class="field"><label for="crawlExperience">경력</label><select id="crawlExperience"><option value="both">신입 + 경력</option><option value="new">신입만</option><option value="career">경력만</option><option value="any">경력 제한 없음</option></select></div>
  <div class="field" id="crawlMaxField"><label for="crawlCareerMax">최대 경력 · 년 (비우면 제한 없음)</label><input id="crawlCareerMax" type="number" min="0" max="30" step="1" placeholder="제한 없음"></div>
  <div class="field"><label for="crawlEducation">학력</label><select id="crawlEducation"><option value="both">학력무관 + 4년제 대졸 이상</option><option value="none">학력무관만</option><option value="university">4년제 대졸 이상만</option><option value="any">학력 제한 없음</option></select></div>
  <div class="fixed-filters" id="crawlCriteriaSummary"></div></div>"""
page = page.replace('<div class="field"><label>적용 조건</label><div class="fixed-filters"><span class="tag">서울 전체</span><span class="tag">신입 ~ 경력 3년</span><span class="tag">학력무관 / 4년제 대졸</span></div></div>', manual_criteria, 1)
page = page.replace('<option value="recent">최근 수집순</option><option value="deadline">마감일순</option><option value="company">회사명순</option>',
                    '<option value="recent">최근 수집순</option><option value="posted_newest">공고등록일 · 최근순</option><option value="posted_oldest">공고등록일 · 오래된순</option><option value="deadline_soon">채용마감일 · D-Day 짧은순</option><option value="deadline_late">채용마감일 · D-Day 긴순</option><option value="company">회사명순</option>', 1)
page = page.replace('<th>공고 / 회사</th><th>분야</th><th>조건</th><th>기술 스택</th><th>상세</th><th></th>',
                    '<th>공고 / 회사</th><th>분야</th><th>조건</th><th>공고등록일</th><th>채용마감일</th><th>사람인 공고</th><th>상세</th>', 1)
page = page.replace('실제 네트워크 요청은 하지 않습니다. 버튼을 누르면 샘플 공고의 추가·중복 갱신과 진행 로그를 시연합니다.',
                    '공고 목록과 상세 페이지를 확인한 뒤 로컬 데이터베이스에 저장합니다.')
page = page.replace('검색어를 입력하고 샘플 수집을 시작하세요.', '검색어를 입력하고 수집을 시작하세요.')
page = page.replace('샘플 데이터 10건이 준비되어 있습니다.', '수집 이력은 이 PC에 저장됩니다.')
page = page.replace('수집을 시작하면 진행 상태가 이곳에 표시됩니다.', '수집을 시작하면 진행 상태가 이곳에 표시됩니다.')
page = page.replace('앱 내 목록 + 모의 Windows 알림', '앱 내 목록 + Windows 알림')
page = page.replace('이 탭이 열려 있을 때', 'PC 앱이 실행 중일 때')
page = page.replace('실제 사이트 요청과 Windows 시스템 알림은 수행하지 않습니다. 설정과 알림은 새로고침하면 초기화됩니다.',
                    '감시 조건과 알림은 로컬에 저장되며 앱을 다시 열어도 유지됩니다.')
page = page.replace('저장된 샘플 공고 상세를 열 수 있습니다.', '저장된 공고 상세를 열 수 있습니다.')
page = page.replace('WINDOWS 알림 시연', '새 공고 알림')
page = page.replace('검색어마다 확인 간격을 정하고, 처음 발견한 공고만 알림으로 받습니다.',
                    '검색어별 감시를 시작하면 설정한 간격으로 새 공고를 확인합니다.')
page = page.replace('여러 검색어를 각각 다른 간격으로 확인',
                    '검색어마다 간격을 정하고 감시 시작으로 자동 확인합니다.')
page = page.replace('간격과 다음 확인 시각을 개별 관리합니다.',
                    '시작한 감시만 앱이 실행 중일 때 자동 확인합니다.')
page = page.replace('추가 직후 첫 확인은 기존 공고를 기준으로 등록합니다. 다음 확인부터 새 공고가 발견되면 알립니다.',
                    '감시 시작 직후 첫 확인에서 기준 목록을 등록합니다. 앱을 다시 열면 감시 시작을 다시 눌러야 합니다.')
page = page.replace('새 공고 알림</small>', '작업 결과 알림</small>')
for field_id, label in (("sectorFilter", "분야"), ("careerFilter", "경력"),
                        ("techFilter", "기술"), ("analysisSector", "분야"),
                        ("analysisCareer", "경력"), ("analysisTech", "기술")):
    old = f'<select id="{field_id}"><option value="">전체 {label}</option></select>'
    new = (f'<details class="multi-filter" id="{field_id}" data-label="{label}">'
           f'<summary>전체 {label}</summary><div class="multi-options">'
           f'<button class="multi-clear" type="button" data-clear-multi="{field_id}">'
           '선택 초기화</button><div class="multi-options-list"></div></div></details>')
    if old not in page:
        raise RuntimeError(f"Missing filter control: {field_id}")
    page = page.replace(old, new, 1)
page = page.replace('<div class="card filter-card"><div class="filter-grid"><div class="field"><label for="analysisKind">',
                    '<div class="card filter-card"><div class="filter-top"><strong>분석 조건</strong><button class="subtle-link" id="analysisClearFilters" type="button">전체 초기화</button></div><div class="filter-grid"><div class="field"><label for="analysisKind">', 1)
page = page.replace('<button class="nav-btn" data-view="fields">',
                    '<button class="nav-btn" data-view="settings"><svg class="nav-icon"><use href="#i-grid"/></svg><span>설정</span></button>\n        <button class="nav-btn" data-view="fields">', 1)
page = page.replace('<button data-view="fields"><svg>',
                    '<button data-view="settings"><svg><use href="#i-grid"/></svg>설정</button><button data-view="fields"><svg>', 1)
settings = """
        <section class="view" id="view-settings" aria-label="설정" hidden>
          <div class="page-head"><div><p class="eyebrow">Settings</p><h1>화면 설정</h1><p class="lead">글자 크기를 앱 전체에 적용하고 다음 실행에도 유지합니다.</p></div></div>
          <div class="card settings-card"><h2>글자 크기</h2><p class="settings-note">사이드바, 목록, 입력창과 공고 상세의 글자 크기를 함께 조절합니다.</p>
            <label for="fontSize" class="settings-value"><output id="fontSizeValue">100%</output></label>
            <input id="fontSize" class="settings-range" type="range" min="80" max="140" step="10" value="100">
            <div><button class="btn" type="button" id="resetFontSize">기본값 100% 복원</button></div>
          </div>
        </section>
"""
page = page.replace('        <section class="view" id="view-fields"',
                    settings + '        <section class="view" id="view-fields"', 1)
page = page.replace(':root{', ':root{--font-scale:1;', 1)
page = page.replace('font-family:Segoe UI', 'font-family:Pretendard,Segoe UI', 1)
page = page.replace('.sidebar{width:232px;', '.sidebar{width:calc(232px * var(--font-scale));', 1)
page = page.replace('</style>', """
    @font-face{font-family:Pretendard;src:url('../../../font/Pretendard-Regular.ttf');font-weight:400}
    @font-face{font-family:Pretendard;src:url('../../../font/Pretendard-Medium.otf');font-weight:500}
    @font-face{font-family:Pretendard;src:url('../../../font/Pretendard-SemiBold.otf');font-weight:600}
    @font-face{font-family:Pretendard;src:url('../../../font/Pretendard-Bold.ttf');font-weight:700}
    @font-face{font-family:Pretendard;src:url('../../../font/Pretendard-ExtraBold.otf');font-weight:800 900}
  </style>""", 1)
page = re.sub(r'font-size:(\d+(?:\.\d+)?)px',
              lambda match: f'font-size:calc({match.group(1)}px * var(--font-scale))', page)
page = re.sub(r'font:(\d+(?:\.\d+)?)px',
              lambda match: f'font:calc({match.group(1)}px * var(--font-scale))', page)
page += '  <script src="qrc:///qtwebchannel/qwebchannel.js"></script>\n  <script src="app.js"></script>\n</body>\n</html>\n'
(root / "desktop" / "src" / "saramin_finder" / "ui" / "index.html").parent.mkdir(parents=True, exist_ok=True)
(root / "desktop" / "src" / "saramin_finder" / "ui" / "index.html").write_text(page, encoding="utf-8")
