let bridge;
let activeView = 'overview';
let explorePage = 1;
let analysisPage = 1;
let groupType = 'sector';
let groupValue = '';
let editingWatchId = null;
let watchers = [];
let regionOptions = [];
let running = false;
let runningWatchId = null;
let toastTimer;

const $ = id => document.getElementById(id);
const esc = value => String(value ?? '').replace(/[&<>"']/g, c =>
  ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const stamp = value => value ? new Date(value).toLocaleString('ko-KR') : '—';
const shortStamp = value => value ? new Date(value).toLocaleDateString('ko-KR') : '—';
function dday(value) {
  if (!value) return '';
  const today = new Date().toLocaleDateString('sv-SE', {timeZone:'Asia/Seoul'});
  const days = Math.round((Date.parse(`${value}T00:00:00Z`) - Date.parse(`${today}T00:00:00Z`)) / 86400000);
  return days < 0 ? '마감됨' : days === 0 ? 'D-Day' : `D-${days}`;
}
function toast(message) {
  const el = $('toast'); el.textContent = message; el.classList.add('show');
  clearTimeout(toastTimer); toastTimer = setTimeout(() => el.classList.remove('show'), 3500);
}
function call(action, data = {}) {
  return new Promise((resolve, reject) => {
    bridge.request(action, JSON.stringify(data), raw => {
      try { const result = JSON.parse(raw); result.ok ? resolve(result.data) : reject(new Error(result.error)); }
      catch (error) { reject(error); }
    });
  });
}
async function safe(action, data = {}) {
  try { return await call(action, data); }
  catch (error) { toast(error.message); return null; }
}
function go(view) {
  activeView = view;
  document.querySelectorAll('.view').forEach(el => el.hidden = el.id !== `view-${view}`);
  document.querySelectorAll('[data-view]').forEach(el => {
    const active = el.dataset.view === view;
    el.classList.toggle('active', active);
    active ? el.setAttribute('aria-current', 'page') : el.removeAttribute('aria-current');
  });
  $('crumbName').textContent = {overview:'대시보드',explore:'공고 데이터',analysis:'요건 분석',
    watch:'공고 감시',crawl:'수집 작업',settings:'설정',fields:'저장 항목'}[view];
  window.scrollTo({top:0,behavior:'smooth'});
  if (view === 'overview') renderOverview();
  if (view === 'explore') renderExplore();
  if (view === 'analysis') renderAnalysis();
  if (view === 'watch') renderWatches();
  if (view === 'crawl') renderRuns();
  if (view === 'fields') renderFields();
}
function techTags(words) {
  return words?.length ? words.slice(0, 3).map(word => `<span class="tag tech">${esc(word)}</span>`).join('') : '—';
}
function statusTag(status) {
  const label = {complete:'완료',image_only:'이미지 공고',failed:'상세 실패',pending:'상세 대기'}[status] || status;
  const cls = status === 'complete' ? 'good' : status === 'image_only' ? 'warn' : 'bad';
  return `<span class="tag ${cls}">${esc(label)}</span>`;
}
async function renderOverview() {
  const [stats, recent] = await Promise.all([safe('dashboard'), safe('postings', {page:1})]);
  if (!stats || !recent) return;
  $('statTotal').textContent = stats.total;
  $('statDetails').textContent = stats.details;
  $('statCompanies').textContent = stats.companies;
  $('statTech').textContent = stats.tech;
  const max = Math.max(1, ...stats.sectors.map(item => item.count));
  $('sectorBars').innerHTML = stats.sectors.length ? stats.sectors.map(item =>
    `<div class="bar-row"><span>${esc(item.value || '미분류')}</span><div class="bar-track"><div class="bar-fill" style="width:${item.count/max*100}%"></div></div><span class="bar-count">${item.count}건</span></div>`
  ).join('') : '<div class="empty">저장된 공고가 없습니다.</div>';
  const run = stats.last_run;
  $('latestState').textContent = run ? ({success:'최근 수집 완료',partial:'일부 수집',failed:'수집 실패'}[run.status] || '수집 중') : '수집 대기 중';
  $('latestSummary').textContent = run ? `“${run.query}” · 신규 ${run.new_count}건, 갱신 ${run.updated_count}건, 상세 실패 ${run.failed_count}건` : '수집 작업에서 첫 검색을 시작하세요.';
  $('latestTime').textContent = run ? stamp(run.finished_at || run.started_at) : '—';
  $('recentRows').innerHTML = recent.items.slice(0, 5).map(item => `<tr>
    <td><span class="job-name">${esc(item.title)}</span><span class="company-name">${esc(item.company)}</span></td>
    <td>${esc(item.sector)}</td><td>${esc(item.career)}</td><td>${techTags(item.tech)}</td>
    <td>${shortStamp(item.last_seen_at)}</td><td><button class="table-action" data-detail="${esc(item.rec_idx)}">열기 →</button></td></tr>`).join('');
}
async function fillFacets() {
  const facets = await safe('facets'); if (!facets) return;
  for (const [id, key, label] of [
    ['companyFilter','company','회사'],['analysisCompany','company','회사'],
    ['analysisQuery','query','검색어']]) {
    const el = $(id); const current = el.value;
    el.innerHTML = `<option value="">전체 ${label}</option>` + facets[key].map(value =>
      `<option value="${esc(value)}">${esc(value)}</option>`).join('');
    el.value = current;
  }
  for (const [id, key] of [['sectorFilter','sector'],['careerFilter','career'],
    ['techFilter','tech'],['analysisSector','sector'],['analysisCareer','career'],
    ['analysisTech','tech']]) fillMulti(id, facets[key]);
}
function multiValues(id) {
  return Array.from($(id).querySelectorAll('.multi-options-list input:checked'), input => input.value);
}
function multiLabel(id) {
  const selected = multiValues(id), el = $(id);
  el.querySelector('summary').textContent = selected.length ?
    `${el.dataset.label} ${selected.length}개 선택` : `전체 ${el.dataset.label}`;
}
function fillMulti(id, values) {
  const selected = new Set(multiValues(id));
  $(id).querySelector('.multi-options-list').innerHTML = values.length ? values.map(value =>
    `<label class="multi-option"><input type="checkbox" value="${esc(value)}" ${selected.has(value) ? 'checked' : ''}><span>${esc(value)}</span></label>`
  ).join('') : '<span class="multi-option">선택할 데이터가 없습니다.</span>';
  multiLabel(id);
}
function clearMulti(id) {
  $(id).querySelectorAll('input:checked').forEach(input => { input.checked = false; });
  multiLabel(id);
}
function applyFontPercent(percent) {
  $('fontSize').value = percent;
  $('fontSizeValue').textContent = `${percent}%`;
  document.documentElement.style.setProperty('--font-scale', String(percent / 100));
}
async function saveFontPercent(percent) {
  const saved = await safe('set_font_percent', {font_percent:percent});
  if (saved) applyFontPercent(saved.font_percent);
}
function exploreFilters() {
  const filters = {text:$('searchInput').value.trim(), company:$('companyFilter').value,
    sector:multiValues('sectorFilter'),career:multiValues('careerFilter'),tech:multiValues('techFilter')};
  if (groupValue) filters[groupType === 'collected' ? 'date' : `group_${groupType}`] = groupValue;
  return filters;
}
async function renderExplore() {
  const [result, groups] = await Promise.all([
    safe('postings', {filters:exploreFilters(),page:explorePage,sort:$('sortSelect').value}),
    safe('groups', {kind:groupType === 'collected' ? 'date' : groupType})]);
  if (!result || !groups) return;
  $('resultCount').textContent = result.total;
  $('resultCaption').textContent = groupValue ? `“${groupValue}” 분류 적용 중` : '저장된 공고를 조건별로 조회';
  $('exploreRows').innerHTML = result.items.map(item => `<tr><td><span class="job-name">${esc(item.title)}</span>
    <span class="company-name">${esc(item.company)} · ID ${esc(item.rec_idx)}</span></td>
    <td>${esc(item.sector)}</td><td>${esc(item.career)}<br><span class="company-name">${esc(item.education)}</span></td>
    <td>${esc(item.posted_date || '미확인')}${!item.posted_date && item.updated_date ? `<br><span class="company-name">수정 ${esc(item.updated_date)}</span>` : ''}</td>
    <td>${esc(item.deadline_date || item.deadline || '미확인')}<br><span class="company-name">${esc(dday(item.deadline_date))}</span></td>
    <td><button class="table-action" data-open-url="${esc(item.url)}">원본 링크 ↗</button></td>
    <td><button class="table-action" data-detail="${esc(item.rec_idx)}">상세 →</button></td></tr>`).join('');
  $('exploreEmpty').hidden = result.total > 0;
  $('visibleSummary').textContent = `${result.total}건 · ${explorePage}페이지`;
  $('groupItems').innerHTML = groups.map(item => `<button class="group-item ${item.value === groupValue ? 'selected' : ''}"
    data-group="${esc(item.value)}" aria-pressed="${item.value === groupValue}"><span>${esc(item.value || '미분류')}</span><b>${item.count}</b></button>`).join('');
  $('explorePrev').disabled = explorePage <= 1;
  $('exploreNext').disabled = explorePage * result.per_page >= result.total;
}
function analysisFilters() {
  return {text:$('analysisText').value.trim(),company:$('analysisCompany').value,
    sector:multiValues('analysisSector'),career:multiValues('analysisCareer'),
    tech:multiValues('analysisTech'),query:$('analysisQuery').value,date:$('analysisDate').value};
}
async function renderAnalysis() {
  const kind = $('analysisKind').value;
  const result = await safe('analysis', {kind,filters:analysisFilters(),page:analysisPage});
  if (!result) return;
  $('analysisCount').textContent = result.total;
  $('analysisPage').textContent = `${analysisPage}페이지`;
  $('analysisRows').innerHTML = result.items.length ? result.items.map(item => `<article class="analysis-row">
    <strong>${esc(item.title)}</strong><small>${esc(item.company)} · ${esc(item.sector)} · ${esc(item.career)} · ${shortStamp(item.last_seen_at)}</small>
    <p>${esc(item.text)}</p><div class="analysis-actions">
      <button class="table-action" type="button" data-detail="${esc(item.rec_idx)}">공고 전체 보기 →</button>
      <button class="table-action" type="button" data-open-url="${esc(item.url)}">브라우저에서 열기 →</button>
    </div>
    </article>`).join('') : '<div class="watch-empty">조건에 맞는 추출 섹션이 없습니다.</div>';
  $('analysisKeywords').innerHTML = result.keywords.length ? result.keywords.map(item =>
    `<button class="analysis-stat" data-analysis-keyword="${esc(item.keyword)}"><span>${esc(item.keyword)}</span><strong>${item.count}건</strong></button>`
  ).join('') : '<div class="watch-empty">분석할 키워드가 없습니다.</div>';
  $('analysisPrev').disabled = analysisPage <= 1;
  $('analysisNext').disabled = analysisPage * 40 >= result.total;
}
async function renderRuns() {
  const runs = await safe('runs'); if (!runs) return;
  $('crawlLog').innerHTML = runs.length ? runs.map(run => `<div class="${run.status === 'failed' ? 'bad' : 'ok'}">
    <time>${esc(stamp(run.started_at))}</time>${esc(run.query)} · ${esc(run.status)}<br>
    DB 첫 저장 ${run.new_count} · 기존 ID 재확인 ${run.updated_count} · 상세 실패 ${run.failed_count}<br>
    ${run.discovered_count == null ? (run.status === 'success' ?
      '비교 기준 없음 · 이번 성공 작업부터 기준 저장' : '비교 지표 미확인 · 성공 작업만 기준으로 사용') :
      `새로 발견 ${run.discovered_count} (등록일로 신규 확인 ${run.registered_count}) · 실제 수정 ${run.changed_count}<br>이번 검색 미검출 ${run.missing_count} (원본 종료 확인 ${run.closed_count})`}
    ${run.error ? ' · ' + esc(run.error) : ''}
    ${run.discovered_count == null ? '' : `<button class="run-events-button" data-run-events="${run.id}">공고별 변화 보기</button><div id="run-events-${run.id}"></div>`}</div>`).join('')
    : '<div>아직 수집 이력이 없습니다.</div>';
}
async function showRunEvents(id) {
  const target = $(`run-events-${id}`);
  if (target.dataset.loaded) { target.hidden = !target.hidden; return; }
  const rows = await safe('run_events', {id}); if (!rows) return;
  const names = {discovered:'새로 발견',registered:'등록일로 신규 확인',changed:'실제 수정',
    missing:'이번 검색 미검출',closed:'원본 종료 확인'};
  target.innerHTML = Object.entries(names).map(([kind,label]) => {
    const items = rows.filter(row => row.kind === kind);
    return `<div class="run-event-group"><strong>${label} ${items.length}건</strong>${items.length ?
      items.map(item => `<button class="run-event-link" data-detail="${esc(item.posting_id)}">${esc(item.company)} · ${esc(item.title)}</button>`).join('') : ''}</div>`;
  }).join('');
  target.dataset.loaded = '1';
}
function profileLabels(profile) {
  const names = Object.fromEntries(regionOptions.map(item => [item.code, item.label]));
  const location = profile.location_codes.length ? profile.location_codes.map(code => names[code] || code).join(' · ') : '지역 제한 없음';
  const hasNew = profile.experience_codes.includes('1'), hasCareer = profile.experience_codes.includes('2');
  const career = !hasNew && !hasCareer ? '경력 제한 없음' :
    `${hasNew ? '신입' : ''}${hasNew && hasCareer ? ' + ' : ''}${hasCareer ? `경력 ${profile.experience_max == null ? '전체' : `최대 ${profile.experience_max}년`}` : ''}`;
  const hasNone = profile.education_codes.includes('0'), hasUniversity = profile.education_codes.includes('8');
  const education = !hasNone && !hasUniversity ? '학력 제한 없음' :
    `${hasNone ? '학력무관' : ''}${hasNone && hasUniversity ? ' + ' : ''}${hasUniversity ? '4년제 대졸 이상' : ''}`;
  return [location, career, education];
}
function syncCriteriaForm(prefix) {
  const unrestricted = $(`${prefix}Nationwide`).checked;
  $(`${prefix}Regions`).querySelectorAll('[data-region-code]').forEach(input => {
    input.disabled = unrestricted;
    if (unrestricted) input.checked = false;
  });
  $(`${prefix}MaxField`).hidden = !['both','career'].includes($(`${prefix}Experience`).value);
  if (prefix === 'crawl') updateCrawlSummary();
}
function fillCriteriaForm(prefix, profile, options) {
  $(`${prefix}Regions`).innerHTML = options.map(item => `<label class="profile-check"><input type="checkbox" data-region-code="${esc(item.code)}" ${profile.location_codes.includes(item.code) ? 'checked' : ''}>${esc(item.label)}</label>`).join('');
  $(`${prefix}Nationwide`).checked = profile.location_codes.length === 0;
  const exp = profile.experience_codes;
  $(`${prefix}Experience`).value = exp.includes('1') && exp.includes('2') ? 'both' : exp.includes('1') ? 'new' : exp.includes('2') ? 'career' : 'any';
  $(`${prefix}CareerMax`).value = profile.experience_max ?? '';
  const edu = profile.education_codes;
  $(`${prefix}Education`).value = edu.includes('0') && edu.includes('8') ? 'both' : edu.includes('0') ? 'none' : edu.includes('8') ? 'university' : 'any';
  syncCriteriaForm(prefix);
}
function criteriaFromForm(prefix) {
  const experience = $(`${prefix}Experience`).value, education = $(`${prefix}Education`).value;
  const locationCodes = $(`${prefix}Nationwide`).checked ? [] :
    Array.from($(`${prefix}Regions`).querySelectorAll('[data-region-code]:checked'), input => input.dataset.regionCode);
  const maxText = $(`${prefix}CareerMax`).value.trim();
  const max = ['both','career'].includes(experience) && maxText !== '' ? Number(maxText) : null;
  if (!$(`${prefix}Nationwide`).checked && !locationCodes.length) throw new Error('지역을 하나 이상 선택하거나 지역 제한 없음을 선택해 주세요.');
  if (max !== null && (!Number.isSafeInteger(max) || max < 0 || max > 30)) throw new Error('최대 경력은 0~30년의 정수로 입력해 주세요.');
  return {location_codes:locationCodes,
    experience_codes:{both:['1','2'],new:['1'],career:['2'],any:[]}[experience],
    experience_max:max,
    education_codes:{both:['0','8'],none:['0'],university:['8'],any:[]}[education]};
}
function updateCrawlSummary() {
  try {
    const labels = profileLabels(criteriaFromForm('crawl'));
    $('crawlCriteriaSummary').innerHTML = labels.map(label => `<span class="tag">${esc(label)}</span>`).join('');
  } catch (_error) { $('crawlCriteriaSummary').textContent = '지역을 선택해 주세요.'; }
}
async function renderProfile() {
  const [profile, options] = await Promise.all([safe('profile'),safe('profile_options')]);
  if (!profile || !options) return;
  regionOptions = options;
  fillCriteriaForm('profile', profile, options);
  fillCriteriaForm('crawl', profile, options);
  $('profileSummary').textContent = `적용 조건 · ${profileLabels(profile).join(' · ')}. 감시 검색어와 간격은 아래에서 각각 수정할 수 있습니다.`;
}
async function saveProfile(event) {
  event.preventDefault();
  $('profileError').textContent = '';
  try {
    const profile = await call('save_profile', criteriaFromForm('profile'));
    $('profileSummary').textContent = `적용 조건 · ${profileLabels(profile).join(' · ')}. 감시 검색어와 간격은 아래에서 각각 수정할 수 있습니다.`;
    await Promise.all([renderWatches(),renderRuns()]);
    toast('검색 조건을 저장했습니다. 다음 감시에서 새 기준 목록을 만듭니다.');
  } catch (error) { $('profileError').textContent = error.message; }
}
async function renderWatches() {
  const [rules, alerts] = await Promise.all([safe('watches'),safe('alerts')]);
  if (!rules || !alerts) return;
  watchers = rules;
  $('watchCount').textContent = rules.length;
  $('alertCount').textContent = alerts.length;
  $('sideAlertCount').textContent = alerts.length;
  $('sideAlertCount').hidden = alerts.length === 0;
  $('watchItems').innerHTML = rules.length ? rules.map(rule => `<article class="watch-item ${rule.active ? '' : 'paused'}">
    <div class="watch-item-top"><div><h3>${esc(rule.query)}</h3><small>${rule.interval_minutes}분 간격 · ${esc(rule.last_result)}</small></div>
    <span class="watch-status ${rule.active ? '' : 'paused'}">${rule.active ? (runningWatchId === rule.id ? '확인 중' : '감시 중') : '중지'}</span></div>
    <div class="watch-item-info"><span>마지막 성공 <b>${esc(stamp(rule.last_success_at))}</b></span>
    <span>다음 확인 <b data-watch-countdown="${rule.id}">${esc(watchDue(rule))}</b></span></div>
    <div class="watch-item-actions"><button class="btn small" data-watch-action="check" data-watch-id="${rule.id}" ${!running ? '' : 'disabled'}>지금 확인</button>
    <button class="btn small" data-watch-action="${rule.active ? 'pause' : 'start'}" data-watch-id="${rule.id}">${rule.active ? '일시정지' : '감시 시작'}</button>
    <button class="btn small" data-watch-action="edit" data-watch-id="${rule.id}">수정</button>
    <button class="btn small danger" data-watch-action="remove" data-watch-id="${rule.id}">삭제</button></div></article>`).join('')
    : '<div class="watch-empty"><strong>설정된 감시가 없습니다</strong>검색어와 간격을 입력해 추가하세요.</div>';
  $('alertList').innerHTML = alerts.length ? alerts.map(alert => `<div class="alert-item"><div class="alert-copy">
    <strong>${esc(alert.title)}</strong><p>${esc(alert.company)} · 감시 검색어 “${esc(alert.query_snapshot)}”</p>
    <time>${esc(stamp(alert.created_at))}</time></div><div class="alert-actions">
    <button class="table-action" type="button" data-detail="${esc(alert.posting_id)}">상세 →</button>
    <button class="table-action" type="button" data-open-url="${esc(alert.url)}">브라우저에서 열기 →</button></div></div>`).join('')
    : '<div class="watch-empty"><strong>새 공고 알림이 없습니다</strong>첫 성공 확인은 기준 목록을 만듭니다.</div>';
}
function watchDue(rule) {
  if (!rule.active) return '감시 시작 대기';
  if (runningWatchId === rule.id) return '확인 중';
  if (!rule.next_due_at) return '확인 예정 없음';
  const remaining = new Date(rule.next_due_at).getTime() - Date.now();
  return remaining <= 0 ? '확인 대기' : `${stamp(rule.next_due_at)} · 약 ${Math.ceil(remaining / 60000)}분 후`;
}
async function renderFields() {
  const fields = [
    ['목록','공고 ID · 회사 · 제목','중복 제거와 공고 식별','rec_idx · company · title'],
    ['목록','분야 · 경력 · 학력','조건별 조회와 분류','sector · career · education'],
    ['날짜','공고등록일 · 수정일 · 채용마감일','공고등록일 및 남은 마감 기간 정렬','posted_date · updated_date · deadline_date'],
    ['출처','사람인 공고 링크','원본 공고 열기','url'],
    ['상세','전체 상세 텍스트','추출 가능한 상세 원문 저장','full_text'],
    ['분석','자격요건 원문','우대사항과 분리된 검색·집계','qualification'],
    ['분석','우대사항 원문','자격요건과 분리된 검색·집계','preference'],
    ['분석','섹션별 기술 키워드','섹션별 서로 다른 공고 수','section_keywords'],
    ['출처','검색어 · 적용 조건 · 시각','수집할 때의 조건 스냅샷','crawl_runs'],
    ['감시','검색어별 주기 · 기준 목록','신규 공고 구별','watch_rules · watch_seen'],
    ['상태','상세·섹션 추출 상태','이미지/실패/제목 없음 구분','detail_status · section_status'],
  ];
  const path = await safe('data_path');
  if (path) fields.push(['보관 위치','로컬 DB 파일','앱 폴더를 옮겨도 같은 PC 계정에 유지됩니다.',path]);
  $('fieldCards').innerHTML = fields.map(([group,title,description,key]) => `<div class="card field-card">
    <span class="badge">${esc(group)}</span><h3>${esc(title)}</h3><p>${esc(description)}</p>
    <span class="field-key">${esc(key)}</span></div>`).join('');
}
async function openDetail(id) {
  const item = await safe('posting', {id}); if (!item) return;
  $('detailTitle').textContent = item.title;
  $('detailSubtitle').textContent = `${item.company} · 공고 ID ${item.rec_idx}`;
  const cells = [['직무 분야',item.sector],['경력 / 학력',`${item.career} / ${item.education}`],
    ['공고등록일',item.posted_date || '미확인'],['최종 수정일',item.updated_date || '미확인'],
    ['채용마감일',item.deadline_date ? `${item.deadline_date} · ${dday(item.deadline_date)}` : item.deadline || '미확인'],
    ['검색어',item.queries.join(', ')],['최근 확인',stamp(item.last_seen_at)],
    ['상세 상태',item.detail_status]];
  const section = (kind,label) => { const value = item.sections[kind] || {text:'',status:'missing'};
    return `<div class="detail-section"><h3>${label} · ${esc(value.status)}</h3><p class="text-panel">${esc(value.text || '추출된 문장이 없습니다.')}</p>
    <div>${techTags(item.keywords[kind])}</div></div>`; };
  $('detailContent').innerHTML = `<div class="detail-meta">${cells.map(([key,value]) =>
    `<div class="meta-cell"><span>${esc(key)}</span><strong>${esc(value)}</strong></div>`).join('')}</div>
    ${section('main_work','주요 업무')}${section('qualification','자격요건')}${section('preference','우대사항')}
    <div class="detail-section"><h3>저장된 상세 전체 텍스트</h3><p class="text-panel">${esc(item.full_text || '읽을 수 있는 상세 텍스트가 없습니다.')}</p></div>
    <div class="detail-section"><h3>원본 공고</h3><button class="table-action" data-open-url="${esc(item.url)}">브라우저에서 열기 →</button></div>`;
  $('detailDialog').showModal();
}
async function startCrawl() {
  const query = $('crawlQuery').value.trim();
  if (!query) { toast('검색어를 입력해 주세요.'); $('crawlQuery').focus(); return; }
  let criteria;
  try { criteria = criteriaFromForm('crawl'); } catch (error) { toast(error.message); return; }
  await safe('collect', {query,pages:Number($('pageCount').value),criteria});
}
function resetWatchForm() {
  editingWatchId = null; $('watchForm').reset(); $('watchInterval').value = '60';
  $('watchFormTitle').textContent = '감시 조건 추가'; $('saveWatch').textContent = '감시 추가';
  $('cancelWatchEdit').hidden = true; $('watchError').textContent = '';
}
async function saveWatch(event) {
  event.preventDefault();
  const query = $('watchQuery').value.trim(), interval = Number($('watchInterval').value);
  try {
    if (!query || query.length > 40 || !Number.isSafeInteger(interval) || interval < 1) throw new Error('검색어와 1분 이상의 정수 간격을 입력해 주세요.');
    await call(editingWatchId ? 'update_watch' : 'add_watch',
      {id:editingWatchId,query,interval});
    resetWatchForm(); await renderWatches(); toast('감시 조건을 저장했습니다.');
  } catch (error) { $('watchError').textContent = error.message; }
}
async function watchAction(button) {
  const id = Number(button.dataset.watchId), rule = watchers.find(item => item.id === id);
  if (!rule) return;
  const action = button.dataset.watchAction;
  if (action === 'edit') {
    editingWatchId = id; $('watchQuery').value = rule.query; $('watchInterval').value = rule.interval_minutes;
    $('watchFormTitle').textContent = '감시 조건 수정'; $('saveWatch').textContent = '변경 저장';
    $('cancelWatchEdit').hidden = false; $('watchQuery').focus(); return;
  }
  if (action === 'remove' && !confirm(`“${rule.query}” 감시 조건을 삭제할까요? 저장된 공고와 알림은 유지됩니다.`)) return;
  const args = {id};
  const method = {check:'check_watch',start:'start_watch',pause:'pause_watch',remove:'delete_watch'}[action];
  if (await safe(method,args)) { if (action === 'remove' && editingWatchId === id) resetWatchForm(); renderWatches(); }
}
function handleEvent(raw) {
  const {name,payload} = JSON.parse(raw);
  if (name === 'started') {
    running = true; runningWatchId = payload.watch_rule_id; $('startCrawl').disabled = true;
    $('crawlStateTitle').textContent = '실제 수집 중';
    $('crawlStateText').textContent = `“${payload.query}” 공고를 확인하고 있습니다.`;
    $('progressFill').style.width = '0%'; $('progressPercent').textContent = '0%';
    renderWatches();
  }
  if (name === 'progress') {
    const message = payload.message || '';
    $('crawlStateText').textContent = message;
    $('progressText').textContent = payload.stage === 'done' ? '완료' : message;
    if (payload.stage === 'done') { $('progressFill').style.width = '100%'; $('progressPercent').textContent = '100%'; }
    const row = document.createElement('div'); row.textContent = `${new Date().toLocaleTimeString('ko-KR')} ${message}`;
    $('crawlLog').prepend(row);
  }
  if (name === 'finished' || name === 'failed') {
    running = false; runningWatchId = null; $('startCrawl').disabled = false;
    const result = payload;
    $('crawlStateTitle').textContent = name === 'failed' || result.status === 'failed' ? '수집 실패' : '수집 완료';
    const summary = result.summary || {title:'수집 실패',message:result.message};
    $('crawlStateText').textContent = summary.message;
    $('progressFill').style.width = '100%'; $('progressPercent').textContent = '100%';
    $('windowAlertTitle').textContent = summary.title;
    $('windowAlertText').textContent = summary.message;
    $('windowAlert').classList.add('show');
    setTimeout(() => $('windowAlert').classList.remove('show'), 7000);
    fillFacets(); renderOverview(); renderExplore(); renderAnalysis(); renderWatches(); renderRuns();
  }
}

document.addEventListener('click', event => {
  const nav = event.target.closest('[data-view]'); if (nav) { go(nav.dataset.view); return; }
  const jump = event.target.closest('[data-go]'); if (jump) { go(jump.dataset.go); return; }
  const detail = event.target.closest('[data-detail]'); if (detail) { openDetail(detail.dataset.detail); return; }
  const runEvents = event.target.closest('[data-run-events]'); if (runEvents) { showRunEvents(Number(runEvents.dataset.runEvents)); return; }
  const group = event.target.closest('[data-group]'); if (group) {
    groupValue = groupValue === group.dataset.group ? '' : group.dataset.group;
    explorePage = 1; renderExplore(); return;
  }
  const action = event.target.closest('[data-watch-action]'); if (action) watchAction(action);
  const keyword = event.target.closest('[data-analysis-keyword]'); if (keyword) {
    const input = Array.from($('analysisTech').querySelectorAll('input')).find(el => el.value === keyword.dataset.analysisKeyword);
    if (input) { input.checked = !input.checked; multiLabel('analysisTech'); analysisPage=1; renderAnalysis(); }
    return;
  }
  const clear = event.target.closest('[data-clear-multi]'); if (clear) {
    const id = clear.dataset.clearMulti; clearMulti(id);
    if (id.startsWith('analysis')) { analysisPage=1;renderAnalysis(); }
    else { explorePage=1;renderExplore(); }
    return;
  }
  const external = event.target.closest('[data-open-url]'); if (external) safe('open_url',{url:external.dataset.openUrl});
});
['searchInput','companyFilter','sortSelect'].forEach(id =>
  $(id).addEventListener(id === 'searchInput' ? 'input' : 'change', () => {explorePage=1;renderExplore();}));
['analysisKind','analysisText','analysisCompany','analysisQuery','analysisDate'].forEach(id =>
  $(id).addEventListener(id === 'analysisText' ? 'input' : 'change', () => {analysisPage=1;renderAnalysis();}));
for (const id of ['sectorFilter','careerFilter','techFilter','analysisSector','analysisCareer','analysisTech']) {
  $(id).addEventListener('change', event => {
    if (!event.target.matches('input[type=checkbox]')) return;
    multiLabel(id);
    if (id.startsWith('analysis')) { analysisPage=1; renderAnalysis(); }
    else { explorePage=1; renderExplore(); }
  });
}
$('groupSelect').addEventListener('change', event => {groupType=event.target.value;groupValue='';renderExplore();});
$('clearFilters').addEventListener('click', () => {
  $('searchInput').value=''; $('companyFilter').value='';
  ['sectorFilter','careerFilter','techFilter'].forEach(clearMulti);
  groupValue='';explorePage=1;$('sortSelect').value='recent';renderExplore();
});
$('analysisClearFilters').addEventListener('click', () => {
  $('analysisText').value=''; $('analysisCompany').value=''; $('analysisQuery').value=''; $('analysisDate').value='';
  ['analysisSector','analysisCareer','analysisTech'].forEach(clearMulti);
  analysisPage=1;renderAnalysis();
});
$('fontSize').addEventListener('input', event => applyFontPercent(Number(event.target.value)));
$('fontSize').addEventListener('change', event => saveFontPercent(Number(event.target.value)));
$('resetFontSize').addEventListener('click', () => saveFontPercent(100));
$('startCrawl').addEventListener('click', startCrawl);
$('resetCrawlCriteria').addEventListener('click', async () => {
  const profile = await safe('profile');
  if (profile) { fillCriteriaForm('crawl', profile, regionOptions); toast('현재 감시 조건을 불러왔습니다.'); }
});
$('watchForm').addEventListener('submit', saveWatch);
$('profileForm').addEventListener('submit', saveProfile);
for (const prefix of ['profile','crawl']) {
  $(`${prefix}Nationwide`).addEventListener('change', () => syncCriteriaForm(prefix));
  $(`${prefix}Experience`).addEventListener('change', () => syncCriteriaForm(prefix));
}
['crawlRegions','crawlCareerMax','crawlEducation'].forEach(id => $(id).addEventListener('change', updateCrawlSummary));
$('cancelWatchEdit').addEventListener('click', resetWatchForm);
$('closeDetail').addEventListener('click', () => $('detailDialog').close());
$('detailDialog').addEventListener('click', event => {if (event.target === $('detailDialog')) $('detailDialog').close();});
$('closeWindowAlert').addEventListener('click', () => $('windowAlert').classList.remove('show'));
$('analysisPrev').addEventListener('click', () => {analysisPage--;renderAnalysis();});
$('analysisNext').addEventListener('click', () => {analysisPage++;renderAnalysis();});
$('exportAnalysis').addEventListener('click', async () => {
  const result = await safe('export_analysis',{kind:$('analysisKind').value,filters:analysisFilters()});
  if (result && !result.cancelled) toast(`${result.count}건을 CSV로 저장했습니다.`);
});
setInterval(() => watchers.forEach(rule => {
  const target = document.querySelector(`[data-watch-countdown="${rule.id}"]`);
  if (target) target.textContent = watchDue(rule);
}), 1000);
const pager = document.createElement('span');
pager.innerHTML = '<button class="btn small" id="explorePrev">이전</button> <button class="btn small" id="exploreNext">다음</button>';
$('visibleSummary').parentElement.appendChild(pager);
$('explorePrev').addEventListener('click', () => {explorePage--;renderExplore();});
$('exploreNext').addEventListener('click', () => {explorePage++;renderExplore();});
new QWebChannel(qt.webChannelTransport, async channel => {
  bridge = channel.objects.bridge;
  bridge.jobEvent.connect(handleEvent);
  const settings = await safe('settings');
  if (settings) applyFontPercent(settings.font_percent);
  await renderProfile();
  await fillFacets();
  await Promise.all([renderOverview(),renderExplore(),renderAnalysis(),renderWatches(),renderRuns(),renderFields()]);
});
