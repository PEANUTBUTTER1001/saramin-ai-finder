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
    isolated = view in ("profile", "crawl", "explore", "filters", "settings", "settings_restore", "alert_link", "crawl_apply", "watch_start")
    sample_db = root / (f"{'settings' if view == 'settings_restore' else view}.sqlite3" if isolated else "live.sqlite3")
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
    if view == "watch" and not store.list_watches():
        rule = store.add_watch("AI", 60)
        store.toggle_watch(rule, False)
    initial_runs = len(store.recent_runs())
    window = AppWindow(store)
    notices = []
    window.bridge.notify = notices.append
    emitted = []
    window.bridge.jobEvent.connect(emitted.append)
    if view in ("crawl_apply", "watch_start"):
        class EmptyClient:
            def search(self, _query, _profile, _page):
                return [], 0
        window.bridge.collector.client_factory = EmptyClient
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
            shown_view = "watch" if view in ("profile", "watch_start", "alert_link") else "crawl" if view == "crawl_apply" else "explore" if view == "filters" else "settings" if view == "settings_restore" else view
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
                window.page().runJavaScript("document.querySelector('[data-watch-action=\"start\"]').click()")
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
                "profileSummary:document.getElementById('profileSummary').textContent,"
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
                "analysisDetail:document.querySelector('#analysisRows [data-detail]')?.dataset.detail})",
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
            "경기 전체" in value.get("profileSummary", "")))
        apply_ok = True
        if view == "crawl_apply":
            import json as json_module
            latest = store.recent_runs(1)
            criteria = json_module.loads(latest[0]["profile_snapshot"]) if latest else {}
            apply_ok = (bool(latest) and latest[0]["query"] == "데이터" and
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
            latest = store.recent_runs(1)
            apply_ok = (bool(latest) and latest[0]["source"] == "watch" and
                        latest[0]["status"] == "success" and len(notices) == 1 and
                        "감시 중" in value.get("watchItemsText", "") and
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
                               value.get("fontAfter") == "18.2px")
        if view == "alert_link":
            ui_ok = ui_ok and (value.get("alertDetail") == "999012" and
                               value.get("alertLink") ==
                               "https://www.saramin.co.kr/zf_user/jobs/relay/view?rec_idx=999012")
        print("profileSaved", profile_ok, flush=True)
        print("manualCriteriaApplied", apply_ok, flush=True)
        print("dateUiReady", ui_ok, flush=True)
        if value.get("analysis") and value.get("bridge") == "object" and profile_ok and ui_ok and apply_ok:
            exit_code["value"] = 0
        def finish():
            shot = root / f"gui-{view}.png"
            print("screenshot", window.grab().save(str(shot)), shot, flush=True)
            app.quit()
        QTimer.singleShot(600, finish)

    window.loadFinished.connect(loaded)
    QTimer.singleShot(18000, app.quit)
    app.exec()
    return exit_code["value"]


if __name__ == "__main__":
    raise SystemExit(main())
