"""Short offscreen smoke test for the portable Qt/HTML app."""

import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

if os.environ.get("SARFINDER_SMOKE_OFFSCREEN") == "1":
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--disable-gpu --disable-gpu-compositing --disable-features=Vulkan"

from PySide6.QtCore import QTimer  # noqa: E402
from PySide6.QtWidgets import QApplication, QSystemTrayIcon  # noqa: E402

from saramin_finder.infrastructure.database import Store  # noqa: E402
from saramin_finder.domain.models import Detail, Posting  # noqa: E402
from saramin_finder.ui.bridge import Bridge  # noqa: E402
from saramin_finder.main import AppWindow  # noqa: E402


def main():
    root = Path(__file__).resolve().parents[1] / ".smoke"
    root.mkdir(exist_ok=True)
    app = QApplication(sys.argv)
    view = sys.argv[1] if len(sys.argv) > 1 else "overview"
    isolated = view in ("profile", "crawl", "explore", "filters", "settings", "settings_restore", "alert_link", "crawl_apply", "watch_start", "workspace", "workspace_restore", "workbench", "workbench_restore")
    db_view = {"settings_restore": "settings", "workspace_restore": "workspace", "workbench_restore": "workbench"}.get(view, view)
    sample_db = root / (f"{db_view}.sqlite3" if isolated else "live.sqlite3")
    store = Store(sample_db if isolated or sample_db.exists() else root / "jobs.sqlite3")
    if view == "settings":
        store.set_font_percent(100)
    if isolated:
        for rule in store.list_watches():
            store.toggle_watch(rule["id"], False)
    if view in ("explore", "filters"):
        today = datetime.now(timezone(timedelta(hours=9))).date()
        closes = today + timedelta(days=5)
        run = store.start_run("manual", "AI", store.get_profile(), 1)
        store.save_posting(Posting(
            "999001", "화면검증회사", "AI 엔지니어", "https://www.saramin.co.kr/zf_user/jobs/relay/view?rec_idx=999001",
            "AI·데이터, 개발", "신입", "학력무관", "서울, 신입, 학력무관", f"~ {closes:%m/%d}",
            today.isoformat(), "", closes.isoformat()),
            Detail(status="complete", sections={"qualification":"Python 경험", "preference":"SQL 우대"},
                   section_status={"qualification":"extracted", "preference":"extracted"}), run)
        if view == "filters":
            store.save_posting(Posting("999002", "두번째회사", "기획자",
                "https://www.saramin.co.kr/zf_user/jobs/relay/view?rec_idx=999002",
                "기획", "경력"), Detail(status="complete", sections={"qualification":"AWS 경험"},
                                         section_status={"qualification":"extracted"}), run)
    if view == "alert_link":
        rule = store.list_watches()[0]["id"]
        store.toggle_watch(rule, True)
        run = store.start_run("manual", "AI", store.get_profile(), 1)
        for posting_id in ("999011", "999012"):
            store.save_posting(Posting(posting_id, "알림검증회사", "새 공고",
                f"https://www.saramin.co.kr/zf_user/jobs/relay/view?rec_idx={posting_id}"),
                Detail(status="failed"), run)
        store.finish_watch(rule, ["999011"])
        store.finish_watch(rule, ["999011", "999012"])
        store.toggle_watch(rule, False)
    if view == "workspace":
        from PySide6.QtWidgets import QFileDialog
        QFileDialog.getSaveFileName = staticmethod(lambda *_args, **_kwargs:
            (str(root / "workspace-export.csv"), "CSV 파일 (*.csv)"))
        store.set_font_percent(100)
        store.set_sidebar_collapsed(False)
        rule = store.list_watches()[0]["id"]
        store.toggle_watch(rule, True)
        run = store.start_run("watch", "AI", store.get_profile(), 1, rule)
        store.save_posting(Posting("999021", "즐겨찾기검증회사", "경력 AI 엔지니어",
            "https://www.saramin.co.kr/zf_user/jobs/relay/view?rec_idx=999021",
            "AI·데이터, 개발", "경력 3~15년", "대졸 이상", deadline="~ 11/30",
            deadline_date="2026-11-30"), Detail(status="failed"), run)
        store.finish_watch(rule, [])
        store.finish_watch(rule, ["999021"])
        store.set_favorite("999021", False)
        store.toggle_watch(rule, False)
    if view == "workbench":
        from PySide6.QtGui import QDesktopServices
        from PySide6.QtWidgets import QFileDialog
        QFileDialog.getSaveFileName = staticmethod(lambda *_args, **_kwargs:
            (str(root / "workbench-export.csv"), "CSV 파일 (*.csv)"))
        store.set_theme("light")
        store.set_font_percent(100)
        store.set_sidebar_collapsed(False)
        rule = store.list_watches()[0]["id"]
        store.toggle_watch(rule, True)
        run = store.start_run("watch", "AI", store.get_profile(), 1, rule)
        for index in range(3):
            posting_id = str(999031 + index)
            store.save_posting(Posting(posting_id, "워크벤치검증회사" if index != 1 else "두번째회사",
                "AI 플랫폼 백엔드 엔지니어 · 데이터 파이프라인 설계 및 운영 자동화" if index == 0 else "AI 서비스 개발자",
                f"https://www.saramin.co.kr/zf_user/jobs/relay/view?rec_idx={posting_id}",
                "AI·데이터, 개발", "경력 3~15년", "대졸 이상", deadline="~ 11/30", deadline_date="2026-11-30"),
                Detail(status="failed") if index == 2 else Detail(status="complete",
                    full_text="AI 서비스 개발\nPython 및 SQL 개발 경험\nAWS와 Docker 운영 우대",
                    sections={"qualification":"Python 및 SQL 개발 경험", "preference":"AWS와 Docker 운영 우대"},
                    section_status={"qualification":"extracted", "preference":"extracted"}), run)
            store.set_favorite(posting_id, index == 2)
        store.finish_watch(rule, [])
        store.finish_watch(rule, ["999031", "999032", "999033"])
        store.toggle_watch(rule, False)
        gamejob_url = "https://www.gamejob.co.kr/Recruit/GI_Read/View?GI_No=999031"
        QDesktopServices.openUrl = staticmethod(lambda url: url.toString() == gamejob_url)
        jobkorea_run = store.start_run("manual", "목록 완료 검증", store.get_profile(), 1, provider="jobkorea")
        store.save_posting(Posting("jobkorea:999031", "잡코리아 검증회사", "AI 분석 개발자",
            gamejob_url, "AI·데이터",
            provider="jobkorea"), Detail(status="complete", sections={"qualification": "Python 개발"},
            section_status={"qualification": "extracted"}), jobkorea_run)
        store.finish_run(jobkorea_run, "partial", 1, 0, 1, listing_complete=True)
        interrupted = store.start_run("manual", "목록 중단 검증", store.get_profile(), 1, provider="jobkorea")
        store.finish_run(interrupted, "partial", 1, 0, 0, "목록 응답 오류", listing_complete=False)
    if view == "watch" and not store.list_watches():
        rule = store.add_watch("AI", 60)
        store.toggle_watch(rule, False)
    if view == "watch_start":
        store.add_watches("AI", 60, ("saramin", "jobkorea"))
        watch_ids = {rule["id"] for rule in store.list_watches()}
    initial_runs = len(store.recent_runs())
    window = AppWindow(store)
    notices = []
    window.bridge.notify = notices.append
    emitted = []
    window.bridge.jobEvent.connect(emitted.append)
    if view in ("crawl_apply", "watch_start"):
        class EmptyClient:
            def search(self, _query, _profile, _page):
                return [], False
        for collector in window.bridge.collectors.values():
            collector.client_factory = EmptyClient
    print("tray", QSystemTrayIcon.isSystemTrayAvailable(), QSystemTrayIcon.supportsMessages(), flush=True)
    window.show()
    exit_code = {"value": 1}

    def loaded(ok):
        print("loadFinished", ok, window.page().url().toString(), flush=True)
        if not ok:
            app.quit()
            return
        window.page().runJavaScript("window.__smokeErrors=[];window.onerror=(msg)=>window.__smokeErrors.push(String(msg))")
        window.page().runJavaScript("window.__smokePostings='pending'; call('postings').then(x=>window.__smokePostings=String(x.total)).catch(e=>window.__smokePostings='ERROR '+e.message)")

        def inspect():
            if view == "workbench_restore":
                window.page().runJavaScript("""
                  window.__workbenchResult={ok:document.body.dataset.theme==='dark' &&
                    document.getElementById('themeSelect').value==='dark' &&
                    document.getElementById('toggleTheme').getAttribute('aria-checked')==='true' &&
                    document.getElementById('themeLabel').textContent==='다크 모드' &&
                    document.getElementById('sidebar').classList.contains('collapsed') &&
                    document.getElementById('fontSizeValue').textContent==='140%'};
                  go('explore');
                """)
                QTimer.singleShot(400, read_state)
                return
            if view == "workbench":
                def run_width(index):
                    width = (900, 1280)[index]
                    window.resize(width, 850)
                    script = """
                      window.__workbenchBatch=null;
                      (async()=>{
                        const check=(ok,message)=>{if(!ok)throw new Error(message)};
                        const pause=()=>new Promise(resolve=>setTimeout(resolve,40));
                        const wait=async button=>{for(let i=0;i<100&&button.disabled;i++)await pause();check(!button.disabled,'request timeout')};
                        const rgb=value=>getComputedStyle(value).color;
                        const contrast=(a,b)=>{
                          const lum=s=>{const v=s.match(/[\\d.]+/g).slice(0,3).map(x=>Number(x)/255).map(x=>x<=.04045?x/12.92:((x+.055)/1.055)**2.4);return .2126*v[0]+.7152*v[1]+.0722*v[2]};
                          const x=lum(a),y=lum(b);return (Math.max(x,y)+.05)/(Math.min(x,y)+.05);
                        };
                        const toggle=document.getElementById('toggleSidebar');
                        check(document.querySelectorAll('#toggleSidebar').length===1,'duplicate sidebar toggle');
                        check(toggle.closest('.topbar-start') && toggle.parentElement.firstElementChild===toggle && toggle.nextElementSibling.classList.contains('crumb'),'toggle not at header start');
                        check(!document.querySelector('#sidebar #toggleSidebar'),'old sidebar toggle remains');
                        check(!document.querySelector('#sidebar .nav-label'),'Workspace label remains');
                        check(document.querySelector('#sideNav [data-view="watch"]').nextElementSibling.dataset.view==='alerts','new postings menu order');
                        check(document.getElementById('sideAlertCount').closest('[data-view]').dataset.view==='alerts','alert badge still on watch');
                        check(!document.querySelector('#view-watch #alertList') && document.querySelector('#view-alerts #alertList'),'alerts not moved');
                        check(!document.getElementById('profileSummary'),'profile summary remains');
                        const watchText=document.getElementById('view-watch').textContent;
                        check(!watchText.includes('감시 방식') && !watchText.includes('실제 앱에서 적용하는 동작') && !watchText.includes('검색어별 감시를 시작하면 설정한 간격으로 새 공고를 확인합니다.'),'watch guidance remains');
                        check(!toggle.textContent.trim() && getComputedStyle(toggle).borderWidth==='0px','toggle has border or text');
                        for(const theme of ['light','dark']){
                          document.getElementById('themeSelect').value=theme;
                          document.getElementById('themeSelect').dispatchEvent(new Event('change',{bubbles:true}));
                          await wait(document.getElementById('themeSelect'));
                          check(document.body.dataset.theme===theme,'theme not applied');
                          const modeSwitch=document.getElementById('toggleTheme');
                          check(modeSwitch.getAttribute('role')==='switch' && modeSwitch.getAttribute('aria-checked')===String(theme==='dark'),'theme switch state');
                          check(modeSwitch.querySelectorAll('svg').length===2 && modeSwitch.querySelector('.switch-sun use').getAttribute('href')==='#i-sun' && modeSwitch.querySelector('.switch-moon use').getAttribute('href')==='#i-moon','sun/moon switch icons');
                          check(getComputedStyle(modeSwitch.querySelector('.switch-thumb')).transform===`matrix(1, 0, 0, 1, ${theme==='dark'?28:0}, 0)`,'switch thumb position');
                          check((await call('settings')).theme===theme,'theme not saved');
                          check(getComputedStyle(document.body).getPropertyValue('--accent').trim().toUpperCase()==='#2D67FF','main color');
                          check(contrast(rgb(document.body),getComputedStyle(document.body).backgroundColor)>=4.5,'body contrast');
                          const surface=getComputedStyle(document.querySelector('.table-wrap')).backgroundColor;
                          check(getComputedStyle(document.querySelector('.multi-filter summary')).backgroundColor===surface,'filter surface does not match theme');
                          if(theme==='dark')for(const selector of ['.watch-item','.analysis-stat','.multi-options','.win-alert']){
                            for(const el of document.querySelectorAll(selector))check(getComputedStyle(el).backgroundColor!=='rgb(255, 255, 255)','legacy light background '+selector);
                          }
                          for(const percent of [80,100,140]){
                            applyFontPercent(percent);
                            for(const section of ['overview','explore','favorites','analysis','watch','alerts','crawl','settings','fields']){
                              go(section);await pause();
                              check(!document.getElementById('view-'+section).hidden,'screen hidden '+section);
                              check(document.documentElement.scrollWidth<=innerWidth+1,'page overflow '+theme+'/'+percent+'/'+section);
                              check(!document.querySelector('.top-actions .demo-pill') && !document.querySelector('.top-actions .local-dot'),'local data header copy remains');
                              const label=document.getElementById('themeLabel').getBoundingClientRect(),mode=document.getElementById('toggleTheme').getBoundingClientRect();
                              check(Math.abs(label.top+label.height/2-mode.top-mode.height/2)<1,'header mode not vertically centered');
                              check(toggle.getBoundingClientRect().right<document.querySelector('.crumb').getBoundingClientRect().left,'toggle overlaps breadcrumb');
                              const left=document.querySelector('.topbar-start').getBoundingClientRect(),right=document.querySelector('.top-actions').getBoundingClientRect();
                              check(left.right<right.left || left.bottom<=right.top,'header sides overlap');
                              check(Math.abs(parseFloat(getComputedStyle(document.querySelector('.nav-btn')).fontSize)-15*percent/100)<.05,'font decrease or scaling');
                              check(Math.abs(parseFloat(getComputedStyle(document.querySelector('.content')).paddingLeft)-(innerWidth<=1100?17.6:24.64))<.05,'content spacing increase');
                              check(Math.abs(parseFloat(getComputedStyle(document.querySelector('.nav')).gap)-1.056)<.05,'menu vertical spacing');
                              check(Math.abs(parseFloat(getComputedStyle(document.getElementById('sidebar')).paddingTop)-10.56)<.05,'sidebar vertical padding');
                              check(Math.abs(parseFloat(getComputedStyle(document.querySelector('.nav-btn')).paddingTop)-7.392)<.05,'sidebar item vertical padding');
                              const cellStyle=getComputedStyle(document.querySelector('#exploreRows td'));
                              check(Math.abs(parseFloat(cellStyle.fontSize)-13*percent/100)<.05,'table font decrease');
                              check(Math.abs(parseFloat(cellStyle.paddingTop)-12.32)<.05,'table padding increase');
                              for(const el of document.querySelectorAll('#view-explore .table-wrap,#view-explore .data-table,#view-explore .data-table :is(thead,tbody,tr,th,td)'))check(getComputedStyle(el).backgroundColor==='rgba(0, 0, 0, 0)','archive table fill remains');
                              if(section==='alerts'){
                                const list=document.getElementById('alertList'),items=[...list.querySelectorAll('.alert-item')];
                                const columns=getComputedStyle(list).gridTemplateColumns.split(' ').length;
                                check(columns>=1 && columns<=3,'alerts exceed three columns');
                                if(innerWidth===1280 && percent===100)check(columns===3,'wide alerts are not three columns');
                                if(innerWidth===900 && percent===100)check(columns===2,'narrow alerts are not two columns');
                                check(items.length===3,'alert content missing');
                                const firstTop=items[0].getBoundingClientRect().top;
                                check(items.filter(el=>Math.abs(el.getBoundingClientRect().top-firstTop)<1).length===columns,'alerts not aligned in a row');
                                for(const item of items){
                                  check(item.scrollWidth<=item.clientWidth+1,'alert content overflows');
                                  const copy=item.querySelector('.alert-copy').getBoundingClientRect(),actions=item.querySelector('.alert-actions').getBoundingClientRect();
                                  check(actions.top>=copy.bottom,'alert actions overlap text');
                                  check(item.querySelector('[data-favorite]') && item.querySelector('[data-detail]') && item.querySelector('[data-open-url]'),'alert action missing');
                                }
                              }
                              if(section==='overview'){
                                const cell=document.querySelector('#recentRows tr')?.cells[4];
                                check(cell && getComputedStyle(cell).whiteSpace==='nowrap','dashboard date wraps');
                                const range=document.createRange();range.selectNodeContents(cell);
                                check(new Set([...range.getClientRects()].map(rect=>rect.top)).size===1,'dashboard date spans lines');
                              }
                              const stat=document.querySelector('.stat');
                              check(getComputedStyle(stat).boxShadow==='none' && getComputedStyle(stat).borderRadius==='0px','card styling remains');
                            }
                          }
                        }
                        go('watch');
                        const allQuery='전체 감시 검증 '+Date.now();
                        document.getElementById('watchProvider').value='all';
                        document.getElementById('watchQuery').value=allQuery;
                        await saveWatch(new Event('submit'));
                        const addedWatches=(await call('watches')).filter(rule=>rule.query===allQuery);
                        check(addedWatches.map(rule=>rule.provider).sort().join(',')==='jobkorea,saramin','all-source watch registration');
                        for(const rule of addedWatches) await call('delete_watch',{id:rule.id});
                        applyFontPercent(100);document.querySelector('#sideNav [data-view="alerts"]').click();await pause();await renderWatches();
                        check(activeView==='alerts' && !document.getElementById('view-alerts').hidden && document.getElementById('crumbName').textContent==='새 공고','new postings navigation');
                        const alertStar=document.querySelector('#alertList [data-favorite]');const alertId=alertStar.dataset.favorite,wasFavorite=alertStar.getAttribute('aria-pressed');
                        await toggleFavorite(alertStar);go('explore');await renderExplore();
                        check(document.querySelector(`#exploreRows [data-favorite="${alertId}"]`).getAttribute('aria-pressed')!==wasFavorite,'alert/explore favorite not shared');
                        await toggleFavorite(document.querySelector(`#exploreRows [data-favorite="${alertId}"]`));
                        go('alerts');await renderWatches();const alertDetail=document.querySelector('#alertList [data-detail]');
                        check(document.querySelector('#alertList [data-open-url]').dataset.openUrl.endsWith('rec_idx='+alertDetail.dataset.detail),'alert link association');
                        await openDetail(alertDetail.dataset.detail);check(document.getElementById('detailDialog').open,'alert detail not open');document.getElementById('closeDetail').click();
                        go('explore');await renderExplore();
                        const group=document.getElementById('groupToggle');group.click();check(!document.getElementById('groupPanel').hidden && group.getAttribute('aria-expanded')==='true','group panel open');group.click();check(document.getElementById('groupPanel').hidden,'group panel close');
                        const action=document.querySelector('#exploreRows [data-detail]');
                        check(getComputedStyle(action).whiteSpace==='nowrap','detail wraps');
                        await openDetail(action.dataset.detail);check(document.getElementById('detailDialog').open,'detail not open');
                        check(document.getElementById('detailContent').textContent.includes('최초 감시 수집'),'detail timestamp missing');
                        document.getElementById('closeDetail').click();
                        const star=document.querySelector('#exploreRows [data-favorite="999031"]');const old=star.getAttribute('aria-pressed');await toggleFavorite(star);check(star.getAttribute('aria-pressed')!==old,'favorite not changed');await toggleFavorite(star);
                        go('favorites');await renderFavorites();check(document.querySelectorAll('#favoriteRows tr').length===1,'favorites not retained');
                        go('explore');document.getElementById('exploreProvider').value='jobkorea';await renderExplore();
                        check(document.querySelectorAll('#exploreRows tr').length===1 && document.querySelector('#exploreRows [data-detail]').dataset.detail==='jobkorea:999031','archive provider filter');
                        await openDetail('jobkorea:999031');
                        check(document.getElementById('detailSubtitle').textContent.includes('잡코리아 · 공고 ID 999031'),'detail provider or original ID missing');
                        const gamejobUrl=document.querySelector('#detailContent [data-open-url]').dataset.openUrl;
                        check((await call('open_url',{url:gamejobUrl})).opened,'gamejob posting link not accepted');
                        document.getElementById('closeDetail').click();
                        go('crawl');await renderRuns();
                        const runLogs=[...document.querySelectorAll('#crawlLog > div')].map(row=>row.textContent);
                        const complete=runLogs.find(text=>text.includes('목록 완료 검증'));
                        const interrupted=runLogs.find(text=>text.includes('목록 중단 검증'));
                        check(complete?.includes('목록 확인 완료') && complete.includes('상세 실패 1') &&
                              complete.includes('다음 목록 비교 기준으로 등록'),'completed list with failed detail mislabeled');
                        check(interrupted?.includes('목록 확인 중단') && interrupted.includes('비교 기준 미등록'),'interrupted list mislabeled');
                        go('analysis');document.getElementById('analysisProvider').value='jobkorea';await renderAnalysis();
                        check(document.getElementById('analysisCount').textContent==='1' && document.getElementById('analysisRows').textContent.includes('잡코리아'),'analysis provider filter');
                        document.getElementById('analysisClearFilters').click();
                        go('explore');document.getElementById('searchInput').value='검색결과없음';await renderExplore();check(!document.getElementById('exploreEmpty').hidden,'empty state missing');
                        document.getElementById('clearFilters').click();await pause();
                        const exportButton=document.getElementById('exportPostings');exportButton.click();await wait(exportButton);check(document.getElementById('toast').textContent.includes('4건'),'CSV failed');
                        const before=document.getElementById('sidebar').classList.contains('collapsed');toggle.click();await wait(toggle);check(document.getElementById('sidebar').classList.contains('collapsed')!==before,'collapse failed');toggle.click();await wait(toggle);check(document.getElementById('sidebar').classList.contains('collapsed')===before,'expand failed');
                        const themeButton=document.getElementById('toggleTheme');themeButton.click();await wait(themeButton);check(document.body.dataset.theme==='light','top theme switch failed');themeButton.click();await wait(themeButton);check(document.body.dataset.theme==='dark','top theme switch failed');
                        window.__workbenchBatch={ok:true,width:innerWidth};
                      })().catch(error=>window.__workbenchBatch={ok:false,error:String(error),stack:error.stack});
                    """
                    window.page().runJavaScript(script)
                    def poll(attempt=0):
                        def result(raw):
                            import json
                            value = json.loads(raw) if raw else None
                            if value is None and attempt < 140:
                                QTimer.singleShot(100, lambda: poll(attempt + 1))
                                return
                            print("workbenchWidth", width, ascii(value), flush=True)
                            if value and value.get("ok") and index == 0:
                                run_width(1)
                            else:
                                window.page().runJavaScript("window.__workbenchResult=window.__workbenchBatch; "
                                    "saveTheme('dark').then(()=>saveFontPercent(140)).then(()=>call('set_sidebar_collapsed',{collapsed:true})).then(()=>applySidebarCollapsed(true));")
                                QTimer.singleShot(700, read_state)
                        window.page().runJavaScript("JSON.stringify(window.__workbenchBatch)", result)
                    QTimer.singleShot(150, poll)
                run_width(0)
                return
            if view in ("workspace", "workspace_restore"):
                script = """
                  (async () => {
                    const assert = (ok, message) => {if (!ok) throw new Error(message)};
                    const checks = [];
                    const tick = () => new Promise(resolve => setTimeout(resolve, 100));
                    const clickStar = async selector => {
                      const button = document.querySelector(selector);
                      assert(button, 'missing star '+selector); button.click();
                      for (let i=0; i<50 && (button.disabled || pendingFavorites.size); i++) await tick();
                      assert(!pendingFavorites.size, 'favorite request timed out');
                    };
                    go('explore'); await renderExplore();
                    const row = document.querySelector('#exploreRows [data-favorite="999021"]').closest('tr');
                    const headers = [...document.querySelectorAll('#view-explore th')].map(el=>el.textContent);
                    const career = row.cells[headers.indexOf('조건')];
                    const deadline = row.cells[headers.indexOf('채용마감일')];
                    const collected = row.cells[headers.indexOf('수집시각')];
                    assert(headers[headers.indexOf('채용마감일')+1] === '수집시각', 'column order');
                    assert(headers[1] === '번호' && headers[2] === '공고 / 회사', 'posting number column order');
                    assert(row.cells[1].textContent === '1', 'posting number');
                    assert(collected.querySelector('.collection-time').getBoundingClientRect().top > collected.querySelector('.collection-date').getBoundingClientRect().top, 'collection time not on second line');
                    assert([...document.querySelectorAll('.brand strong')].map(el=>el.textContent).join('/') === 'Saramin/Finder', 'brand text');
                    assert(!document.querySelector('.brand small') && !document.querySelector('.sidebar-bottom'), 'redundant sidebar copy');
                    for (const percent of [80,100,140]) {
                      applyFontPercent(percent);
                      for (const width of [900,1280]) {
                        document.querySelector('.app').style.width = width+'px';
                        for (const el of [career.querySelector('span'),deadline,row.querySelector('[data-detail]')]) {
                          assert(getComputedStyle(el).whiteSpace === 'nowrap', 'wrapping enabled');
                          const range=document.createRange();range.selectNode(el.firstChild);
                          const rects=[...range.getClientRects()];
                          assert(new Set(rects.map(rect=>rect.top)).size === 1, 'text wraps');
                        }
                      }
                    }
                    document.querySelector('.app').style.width = '';applyFontPercent(100);
                    assert(career.textContent.includes('경력 3~15년'), 'career text');
                    assert(deadline.textContent.includes('2026-11-30'), 'deadline text');
                    assert(collected.textContent.includes('감시 수집'), 'collection timestamp');
                    checks.push('date/career no wrap at 80/100/140%, 900/1280px', 'collection time on second line', 'posting number column', 'sidebar brand and footer');
                    if (!window.__restoreWorkspace) {
                      const exportButton=document.getElementById('exportPostings');
                      assert(exportButton, 'missing archive CSV button');exportButton.click();
                      for(let i=0;i<50 && exportButton.disabled;i++) await tick();
                      assert(!exportButton.disabled && document.getElementById('toast').textContent.includes('1건'), 'CSV export failed');
                      checks.push('archive CSV export via bridge');
                    }
                    if (window.__restoreWorkspace) {
                      assert(document.getElementById('sidebar').classList.contains('collapsed'), 'sidebar not restored');
                      go('favorites');await renderFavorites();
                      assert(document.querySelectorAll('#favoriteRows tr').length === 1, 'favorite not restored');
                      checks.push('sidebar and favorites restored');
                    } else {
                      go('alerts'); await renderWatches();
                      await clickStar('#alertList [data-favorite="999021"]');
                      assert(document.querySelector('#exploreRows [data-favorite="999021"]').getAttribute('aria-pressed') === 'true', 'explore not synchronized');
                      go('favorites'); await renderFavorites();
                      assert(document.querySelectorAll('#favoriteRows tr').length === 1, 'favorite missing');
                      await clickStar('#favoriteRows [data-favorite="999021"]');
                      assert(document.querySelectorAll('#favoriteRows tr').length === 0 && !document.getElementById('favoriteEmpty').hidden, 'favorite not removed');
                      assert(document.querySelector('#alertList [data-favorite="999021"]').getAttribute('aria-pressed') === 'false', 'alert not synchronized');
                      go('explore');await renderExplore();
                      await clickStar('#exploreRows [data-favorite="999021"]');
                      checks.push('alert/explore/favorites toggle and synchronization', 'empty favorites state');
                      const sidebar=document.getElementById('sidebar');
                      const expanded=sidebar.getBoundingClientRect().width;
                      assert(expanded === 164 && getComputedStyle(document.querySelector('#sideNav .nav-btn')).paddingTop === '7px', 'sidebar spacing');
                      const toggle=document.getElementById('toggleSidebar');
                      assert(!toggle.textContent.trim() && getComputedStyle(toggle).borderWidth === '0px', 'toggle text or border remains');
                      const toggleOnce=async()=>{toggle.click();for(let i=0;i<50 && toggle.disabled;i++) await tick();assert(!toggle.disabled,'sidebar request timed out')};
                      await toggleOnce();
                      assert(sidebar.getBoundingClientRect().width === 68 && toggle.getAttribute('aria-expanded') === 'false', 'collapse failed');
                      assert([...document.querySelectorAll('#sideNav .nav-btn span')].every(el=>getComputedStyle(el).display==='none'), 'labels visible');
                      assert([...document.querySelectorAll('#sideNav .nav-btn')].every(el=>el.title && el.getAttribute('aria-label')), 'missing icon labels');
                      await toggleOnce();
                      assert(sidebar.getBoundingClientRect().width === expanded && toggle.getAttribute('aria-expanded') === 'true', 'expand failed');
                      await toggleOnce();go('favorites');await renderFavorites();
                      checks.push('sidebar collapse/expand/collapse');
                    }
                    await openDetail('999021');
                    assert(document.getElementById('detailContent').textContent.includes('최초 감시 수집'), 'missing detail timestamp');
                    document.getElementById('detailDialog').close();
                    window.__workspaceResult={ok:true,checks};
                  })().catch(error=>window.__workspaceResult={ok:false,error:String(error)})
                """
                window.page().runJavaScript(f"window.__restoreWorkspace={str(view == 'workspace_restore').lower()};" + script)
                QTimer.singleShot(3500, read_state)
                return
            shown_view = "watch" if view in ("profile", "watch_start") else "alerts" if view == "alert_link" else "crawl" if view == "crawl_apply" else "explore" if view == "filters" else "settings" if view == "settings_restore" else view
            window.page().runJavaScript(f"go({shown_view!r})")
            if view == "profile":
                window.page().runJavaScript("""
                  document.querySelector('[data-region-code="101000"]').checked=false;
                  document.querySelector('[data-region-code="102000"]').checked=true;
                  document.getElementById('profileExperience').value='career';
                  document.getElementById('profileCareerMax').value='5';
                  document.getElementById('profileEducation').value='university';
                  document.getElementById('profileForm').dispatchEvent(
                    new Event('submit',{bubbles:true,cancelable:true}));
                """)
                QTimer.singleShot(1500, read_state)
            elif view == "crawl_apply":
                window.page().runJavaScript("""
                  document.getElementById('crawlProvider').value='jobkorea';
                  document.getElementById('crawlProvider').dispatchEvent(new Event('change'));
                  document.getElementById('crawlQuery').value='데이터';
                  document.getElementById('pageCount').value='1';
                  document.querySelectorAll('#crawlRegions [data-region-code]').forEach(x=>x.checked=x.dataset.regionCode==='102000');
                  document.getElementById('crawlExperience').value='career';
                  document.getElementById('crawlCareerMax').value='2';
                  document.getElementById('crawlEducation').value='university';
                  document.getElementById('startCrawl').click();
                """)
                QTimer.singleShot(1500, read_state)
            elif view == "watch_start":
                window.page().runJavaScript("document.getElementById('startAllWatches').click()")
                QTimer.singleShot(1500, read_state)
            elif view == "filters":
                window.page().runJavaScript("""
                  const sector=document.querySelectorAll('#sectorFilter .multi-options-list input');
                  [...sector].filter(x=>['개발','기획'].includes(x.value)).forEach(x=>{x.checked=true;x.dispatchEvent(new Event('change',{bubbles:true}))});
                  go('analysis');
                  const tech=[...document.querySelectorAll('#analysisTech .multi-options-list input')];
                  tech.filter(x=>['Python','AWS'].includes(x.value)).forEach(x=>{x.checked=true;x.dispatchEvent(new Event('change',{bubbles:true}))});
                """)
                QTimer.singleShot(1200, read_state)
            elif view == "settings":
                window.page().runJavaScript("""
                  window.__fontBefore=getComputedStyle(document.querySelector('.nav-btn')).fontSize;
                  const slider=document.getElementById('fontSize');slider.value='140';
                  slider.dispatchEvent(new Event('input',{bubbles:true}));
                  slider.dispatchEvent(new Event('change',{bubbles:true}));
                """)
                QTimer.singleShot(1200, read_state)
            else:
                read_state()

        def read_state():
            window.page().runJavaScript("1+1", lambda value: print("jsArithmetic", ascii(value), flush=True))
            for name, expression in (
                ("title", "document.title"),
                ("bodyLength", "document.body ? document.body.innerHTML.length : -1"),
                ("analysisExists", "!!document.getElementById('view-analysis')"),
                ("bridgeType", "typeof bridge"),
                ("totalExists", "!!document.getElementById('statTotal')"),
            ):
                window.page().runJavaScript(expression, lambda value, key=name: print(key, ascii(value), flush=True))
            window.page().runJavaScript(
                "JSON.stringify({title:document.title,analysis:!!document.getElementById('view-analysis'),"
                "bridge:typeof bridge, total:document.getElementById('statTotal').textContent,"
                "analysisCount:document.getElementById('analysisCount').textContent,"
                "analysisRows:document.getElementById('analysisRows').textContent.length,"
                "watchCount:document.getElementById('watchCount').textContent,"
                "watchItemsText:document.getElementById('watchItems').textContent.slice(0,300),"
                "profileSelectedRegions:[...document.querySelectorAll('#profileRegions input:checked')].map(el=>el.dataset.regionCode),"
                "crawlRegions:document.querySelectorAll('#crawlRegions input:checked').length,"
                "sortOptions:[...document.getElementById('sortSelect').options].map(x=>x.value),"
                "postingsCall:window.__smokePostings,"
                "crawlState:document.getElementById('crawlStateTitle').textContent,"
                "popupText:document.getElementById('windowAlertText').textContent,"
                "smokeErrors:window.__smokeErrors,"
                "running:running,"
                "bridgeEventType:typeof bridge.jobEvent,"
                "bridgeKeys:Object.keys(bridge),"
                "resetButton:!!document.getElementById('resetCrawlCriteria'),"
                "exploreText:document.getElementById('exploreRows').textContent.slice(0,300),"
                "originalLinks:document.querySelectorAll('#exploreRows [data-open-url]').length,"
                "sectorValues:multiValues('sectorFilter'),analysisTechValues:multiValues('analysisTech'),"
                "fontBefore:window.__fontBefore,fontAfter:getComputedStyle(document.querySelector('.nav-btn')).fontSize,"
                "fontFamily:getComputedStyle(document.querySelector('.nav-btn')).fontFamily,"
                "fontLoaded:document.fonts.check('400 12px Pretendard'),"
                "fontValue:document.getElementById('fontSizeValue').textContent,"
                "settingTab:!!document.querySelector('[data-view=settings]'),"
                "alertLink:document.querySelector('#alertList [data-open-url]')?.dataset.openUrl,"
                "alertDetail:document.querySelector('#alertList [data-detail]')?.dataset.detail,"
                "analysisLink:document.querySelector('#analysisRows [data-open-url]')?.dataset.openUrl,"
                "analysisDetail:document.querySelector('#analysisRows [data-detail]')?.dataset.detail,"
                "workspaceResult:window.__workspaceResult,workbenchResult:window.__workbenchResult,"
                "fontScale:getComputedStyle(document.documentElement).getPropertyValue('--font-scale').trim()})",
                checked)

        QTimer.singleShot(2500, inspect)

    def checked(result):
        print("pageState", ascii(result), flush=True)
        print("bridgeSignals", len(emitted), "notices", len(notices), flush=True)
        import json
        value = json.loads(result) if result else {}
        profile_ok = (view != "profile" or (
            store.get_profile().location_codes == ("102000",) and
            store.get_profile().experience_codes == ("2",) and
            store.get_profile().experience_max == 5 and
            store.get_profile().education_codes == ("8",) and
            "102000" in value.get("profileSelectedRegions", [])))
        apply_ok = True
        if view == "crawl_apply":
            import json as json_module
            latest = store.recent_runs(1)
            criteria = json_module.loads(latest[0]["profile_snapshot"]) if latest else {}
            apply_ok = (bool(latest) and latest[0]["query"] == "데이터" and
                        latest[0]["provider"] == "jobkorea" and
                        latest[0]["status"] == "success" and
                        criteria.get("location_codes") == ["102000"] and
                        criteria.get("experience_codes") == ["2"] and
                        criteria.get("experience_max") == 2 and
                        criteria.get("education_codes") == ["8"] and
                        store.get_profile().location_codes == ("101000",) and
                        len(notices) == 1 and
                        value.get("crawlState") == "수집 완료" and
                        "상세 실패" in value.get("popupText", ""))
        elif view == "watch_start":
            latest = store.recent_runs(len(watch_ids))
            apply_ok = (len(notices) == len(watch_ids) and
                        {run["watch_rule_id"] for run in latest} == watch_ids and
                        all(run["source"] == "watch" and run["status"] == "success" for run in latest) and
                        all(store.get_watch(rule_id)["baseline_ready"] for rule_id in watch_ids) and
                        value.get("watchItemsText", "").count("감시 중") == len(watch_ids) and
                        "상세 실패" in value.get("popupText", ""))
        elif view in ("crawl", "watch"):
            apply_ok = (len(store.recent_runs()) == initial_runs and len(notices) == 0 and
                        (view != "watch" or "감시 시작" in value.get("watchItemsText", "")))
        ui_ok = (view not in ("crawl", "explore") or (
            value.get("crawlRegions", 0) > 0 and
            {"posted_newest", "posted_oldest", "deadline_soon", "deadline_late"}.issubset(
                set(value.get("sortOptions", []))) and
            str(value.get("postingsCall", "")).isdigit() and value.get("resetButton")))
        if view == "explore":
            ui_ok = ui_ok and ("화면검증회사" in value.get("exploreText", "") and
                               "D-5" in value.get("exploreText", "") and
                               value.get("originalLinks", 0) > 0)
        if view == "filters":
            ui_ok = ui_ok and (set(value.get("sectorValues", [])) == {"개발", "기획"} and
                               set(value.get("analysisTechValues", [])) == {"Python", "AWS"} and
                               value.get("analysisCount") == "2" and
                               value.get("analysisLink", "").endswith(
                                   f"rec_idx={value.get('analysisDetail')}") and
                               value.get("settingTab"))
        if view == "settings":
            ui_ok = ui_ok and (store.get_font_percent() == 140 and value.get("fontValue") == "140%" and
                               value.get("fontBefore") != value.get("fontAfter") and
                               "Pretendard" in value.get("fontFamily", "") and value.get("fontLoaded"))
        if view == "settings_restore":
            ui_ok = ui_ok and (store.get_font_percent() == 140 and value.get("fontValue") == "140%" and
                               value.get("fontScale") == "1.4")
        if view == "alert_link":
            ui_ok = ui_ok and (value.get("alertDetail") == "999012" and
                               value.get("alertLink") ==
                               "https://www.saramin.co.kr/zf_user/jobs/relay/view?rec_idx=999012")
        if view in ("workspace", "workspace_restore"):
            ui_ok = ui_ok and value.get("workspaceResult", {}).get("ok", False)
            if view == "workspace":
                import csv
                with (root / "workspace-export.csv").open(encoding="utf-8-sig", newline="") as stream:
                    rows = list(csv.DictReader(stream))
                ui_ok = ui_ok and len(rows) == 1 and rows[0]["공고 ID"] == "999021"
        if view in ("workbench", "workbench_restore"):
            ui_ok = ui_ok and value.get("workbenchResult", {}).get("ok", False)
            ui_ok = ui_ok and store.get_theme() == "dark" and store.get_sidebar_collapsed() and store.get_font_percent() == 140
            if view == "workbench":
                import csv
                with (root / "workbench-export.csv").open(encoding="utf-8-sig", newline="") as stream:
                    rows = list(csv.DictReader(stream))
                ui_ok = ui_ok and len(rows) == 4 and {
                    (row["공고 ID"], row["출처"]) for row in rows
                } == {("999031", "사람인"), ("999032", "사람인"), ("999033", "사람인"), ("999031", "잡코리아")}
        print("profileSaved", profile_ok, flush=True)
        print("manualCriteriaApplied", apply_ok, flush=True)
        print("dateUiReady", ui_ok, flush=True)
        if value.get("analysis") and value.get("bridge") == "object" and profile_ok and ui_ok and apply_ok and not value.get("smokeErrors"):
            exit_code["value"] = 0
        def finish():
            shot = root / f"gui-{view}.png"
            print("screenshot", window.grab().save(str(shot)), shot, flush=True)
            if view == "workbench":
                def light_shot():
                    shot = root / "gui-workbench-light.png"
                    print("screenshot", window.grab().save(str(shot)), shot, flush=True)
                    app.quit()
                def dark_shot():
                    shot = root / "gui-workbench-dark.png"
                    print("screenshot", window.grab().save(str(shot)), shot, flush=True)
                    def dashboard_shot():
                        shot = root / "gui-workbench-dashboard.png"
                        print("screenshot", window.grab().save(str(shot)), shot, flush=True)
                        window.page().runJavaScript("applyTheme('light');go('explore')", lambda _value: QTimer.singleShot(200, light_shot))
                    def alerts_shot():
                        shot = root / "gui-workbench-alerts.png"
                        print("screenshot", window.grab().save(str(shot)), shot, flush=True)
                        window.page().runJavaScript("go('overview')", lambda _value: QTimer.singleShot(400, dashboard_shot))
                    window.page().runJavaScript("go('alerts')", lambda _value: QTimer.singleShot(400, alerts_shot))
                window.page().runJavaScript("applyFontPercent(100);applySidebarCollapsed(false);applyTheme('dark');go('explore');document.getElementById('toast').classList.remove('show')",
                    lambda _value: QTimer.singleShot(250, dark_shot))
                return
            if view == "workspace":
                def expanded_shot():
                    shot = root / "gui-workspace-expanded.png"
                    print("screenshot", window.grab().save(str(shot)), shot, flush=True)
                    app.quit()
                window.page().runJavaScript("applySidebarCollapsed(false)",
                    lambda _value: QTimer.singleShot(200, expanded_shot))
                return
            app.quit()
        QTimer.singleShot(600, finish)

    window.loadFinished.connect(loaded)
    QTimer.singleShot(40000 if view == "workbench" else 18000, app.quit)
    app.exec()
    return exit_code["value"]


if __name__ == "__main__":
    raise SystemExit(main())
