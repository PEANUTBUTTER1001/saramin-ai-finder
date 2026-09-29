from dataclasses import replace
from datetime import date, timedelta
import json
import sqlite3

import pytest

from saramin_finder.domain.models import Detail, Posting, SearchProfile
from saramin_finder.domain.rules import extract_sections, keywords_in, sector_keywords, valid_education
from saramin_finder.infrastructure.database import Store
from saramin_finder.infrastructure.saramin import (SaraminClient, deadline_date,
                                                   explicit_closure, listing_dates,
                                                   parse_detail, parse_list, search_params)
from saramin_finder.infrastructure.saramin import CrawlError
from saramin_finder.usecases.analyze import export_rows
from saramin_finder.infrastructure.csv_export import write_csv
from saramin_finder.usecases.collect import Collector


def test_request_delay_includes_retries(monkeypatch):
    import saramin_finder.infrastructure.saramin as saramin
    sleeps = []
    monkeypatch.setattr(saramin.time, "sleep", sleeps.append)
    monkeypatch.setattr(saramin.random, "uniform", lambda low, high: 0.75)

    class Response:
        text = "<html>ok</html>"
        def raise_for_status(self):
            return None

    class Session:
        def __init__(self):
            self.headers = {}
            self.calls = 0
        def get(self, *_args, **_kwargs):
            self.calls += 1
            if self.calls == 2:
                raise saramin.requests.ConnectionError("temporary")
            return Response()

    session = Session()
    client = SaraminClient(session)
    client._get("https://www.saramin.co.kr/test", {})
    client._get("https://www.saramin.co.kr/test", {})
    assert session.calls == 3
    assert sleeps == [0.75, 1, 0.75]


def test_closure_requires_explicit_site_message():
    assert explicit_closure("<div class='close_notice'>본 채용정보는 마감되었습니다.</div>")
    assert not explicit_closure("<div class='user_content'>본 채용정보는 마감되었습니다.</div>")
    assert not explicit_closure("<h1>접근이 제한되었습니다</h1>")


def sample_post(rec_idx="123"):
    return Posting(rec_idx, "테스트회사", "AI 개발자", "https://www.saramin.co.kr/job/123",
                   "AI·데이터", "신입", "학력무관", "서울, 신입, 학력무관", "상시채용")


def sample_detail():
    return parse_detail("""<div class='user_content'><h2>AI 개발자</h2>
       <h3>주요업무</h3><p>AI 서비스를 만듭니다.</p>
       <h3>자격요건</h3><p>Python과 SQL 개발 경험</p>
       <h3>우대사항</h3><p>AWS 및 Docker 운영 경험</p>
       <h3>복리후생</h3><p>식사 제공</p></div>""")


def test_sector_keywords_discard_blanks_and_duplicates():
    assert sector_keywords(" AI·데이터, 개발 ,AI·데이터, , 개발 ") == ("AI·데이터", "개발")


def test_sector_migration_and_multi_filters_preserve_existing_postings(tmp_path):
    path = tmp_path / "jobs.sqlite3"
    store = Store(path)
    run = store.start_run("manual", "AI", store.get_profile(), 1)
    store.save_posting(replace(sample_post("1"), sector="AI·데이터, 개발, AI·데이터"), sample_detail(), run)
    store.save_posting(replace(sample_post("2"), sector="개발, 기획", career="경력"), sample_detail(), run)
    store.save_posting(replace(sample_post("3"), sector="영업", career="신입"), sample_detail(), run)
    with sqlite3.connect(path) as con:
        con.execute("DROP TABLE posting_sector_keywords")
        con.execute("DROP TABLE app_settings")
        con.execute("PRAGMA user_version=5")
    store = Store(path)
    assert store.dashboard()["total"] == 3
    assert store.get_posting("1")["sector"] == "AI·데이터, 개발, AI·데이터"
    assert store.facets()["sector"] == ["AI·데이터", "개발", "기획", "영업"]
    assert store.list_postings({"sector":["AI·데이터","기획"]})["total"] == 2
    assert store.list_postings({"sector":["AI·데이터","기획"], "career":["신입"]})["total"] == 1
    assert store.list_postings({"sector":["개발"], "tech":["Python","AWS"]})["total"] == 2
    assert store.analyze("qualification", {"tech":["AWS"]})["total"] == 0
    filters = {"sector":["개발"], "career":["경력"], "tech":["Python","AWS"]}
    assert store.analyze("qualification", filters)["total"] == 1
    assert len(list(export_rows(store, "qualification", filters))) == 2  # Header plus one posting.
    assert store.groups("sector")[0] == {"value":"개발", "count":2}
    assert store.list_postings({"sector":["AI·데이터","기획"], "group_sector":"기획"})["total"] == 1
    store.save_posting(replace(sample_post("2"), sector="기획"), sample_detail(), run)
    assert store.list_postings({"sector":["개발"]})["total"] == 1


def test_font_setting_validates_and_persists(tmp_path):
    path = tmp_path / "jobs.sqlite3"
    store = Store(path)
    assert store.get_font_percent() == 100
    assert store.set_font_percent(140) == 140
    assert Store(path).get_font_percent() == 140
    for value in (79, 85, 141, True, "100"):
        with pytest.raises(ValueError):
            store.set_font_percent(value)


def test_search_profile_is_data_driven():
    profile = SearchProfile(location_codes=("101000", "102000"), experience_max=5)
    params = search_params("AI", profile, 2)
    assert params["loc_mcd"] == "101000,102000"
    assert params["exp_max"] == "5"
    assert params["recruitPage"] == "2"


def test_list_parser_keeps_original_filters():
    html = """<div class='item_recruit'><strong class='corp_name'>회사</strong>
      <h2 class='job_tit'><a href='/zf_user/jobs/relay/view?rec_idx=123' title='AI 엔지니어'>AI</a></h2>
      <div class='job_condition'><span>서울</span><span>신입</span><span>학력무관</span></div>
      <div class='job_sector'>AI·데이터</div><div class='job_date'><span class='date'>상시채용</span></div>
      </div>"""
    jobs, raw = parse_list(html, "AI")
    assert raw == 1
    assert len(jobs) == 1
    assert jobs[0].rec_idx == "123"


def test_listing_dates_keep_registration_distinct_from_modification():
    assert listing_dates("등록일 26/09/28") == ("2026-09-28", "")
    assert listing_dates("수정일 26/09/28") == ("", "2026-09-28")
    assert listing_dates("수정일 26/13/01") == ("", "")
    assert deadline_date("~ 10/11(일)", date(2026, 9, 28)) == "2026-10-11"
    assert deadline_date("~ 01/02(금)", date(2026, 12, 31)) == "2027-01-02"
    assert deadline_date("상시채용", date(2026, 9, 28)) == ""
    html = """<div class='item_recruit'><strong class='corp_name'>회사</strong>
      <h2 class='job_tit'><a href='/zf_user/jobs/relay/view?rec_idx=123' title='AI 엔지니어'>AI</a></h2>
      <div class='job_condition'><span>서울</span><span>신입</span><span>학력무관</span></div>
      <div class='job_sector'>AI·데이터 <span class='job_day'>수정일 26/09/28</span></div>
      <div class='job_date'><span class='date'>~ 2026/10/11(일)</span></div></div>"""
    item = parse_list(html, "AI")[0][0]
    assert item.posted_date == "" and item.updated_date == "2026-09-28"
    assert item.deadline_date == "2026-10-11" and item.sector == "AI·데이터"


def test_zero_result_title_does_not_collect_sponsored_cards():
    html = """<title>검색어 채용정보 | 총 0건의 검색결과 - 사람인</title>
      <div class='item_recruit'><h2 class='job_tit'><a href='/zf_user/jobs/relay/view?rec_idx=123'>AI</a></h2></div>"""
    assert parse_list(html, "AI") == ([], 0)


def test_sections_and_keyword_sets_are_separate():
    detail = sample_detail()
    assert detail.status == "complete"
    assert "Python" in detail.sections["qualification"]
    assert "AWS" not in detail.sections["qualification"]
    assert "AWS" in detail.sections["preference"]
    assert "Python" not in detail.sections["preference"]
    assert "Python" in keywords_in(detail.sections["qualification"])
    assert "AWS" in keywords_in(detail.sections["preference"])
    assert "식사 제공" not in detail.sections["preference"]


def test_missing_section_is_not_invented():
    sections, statuses = extract_sections("자격요건\nPython 사용 경험\n복리후생\n식사 제공")
    assert sections["preference"] == ""
    assert statuses["preference"] == "missing"


def test_store_deduplicates_preserves_detail_and_analyzes(tmp_path):
    path = tmp_path / "jobs.sqlite3"
    store = Store(path)
    profile = store.get_profile()
    run = store.start_run("manual", "AI", profile, 1)
    assert store.save_posting(sample_post(), sample_detail(), run)
    assert not store.save_posting(sample_post(), Detail(status="failed"), run)
    assert store.dashboard()["total"] == 1
    assert store.get_posting("123")["detail_status"] == "complete"
    qualification = store.analyze("qualification")
    preference = store.analyze("preference")
    assert qualification["total"] == preference["total"] == 1
    assert "Python" in [x["keyword"] for x in qualification["keywords"]]
    assert "AWS" not in [x["keyword"] for x in qualification["keywords"]]
    assert "AWS" in [x["keyword"] for x in preference["keywords"]]
    assert "Python" not in [x["keyword"] for x in preference["keywords"]]
    assert Store(path).get_posting("123")["sections"]["qualification"]["text"]


def test_watch_baseline_dedupe_and_independent_rules(tmp_path):
    store = Store(tmp_path / "jobs.sqlite3")
    run = store.start_run("manual", "AI", store.get_profile(), 1)
    store.save_posting(sample_post(), sample_detail(), run)
    first = store.list_watches()[0]["id"]
    second = store.add_watch("백엔드", 3)
    assert store.finish_watch(first, ["123"]) == []
    assert store.finish_watch(first, ["123"]) == []
    assert store.finish_watch(second, ["123"]) == []
    store.save_posting(sample_post("456"), sample_detail(), run)
    assert len(store.finish_watch(first, ["123", "456"])) == 1
    assert store.finish_watch(first, ["456"]) == []
    assert len(store.finish_watch(second, ["123", "456"])) == 1
    assert len(store.alerts()) == 2


def test_profile_change_resets_watch_baseline(tmp_path):
    store = Store(tmp_path / "jobs.sqlite3")
    run = store.start_run("manual", "AI", store.get_profile(), 1)
    store.save_posting(sample_post(), sample_detail(), run)
    rule = store.list_watches()[0]["id"]
    store.finish_watch(rule, ["123"])
    updated = store.save_profile(replace(store.get_profile(), experience_max=5))
    assert updated.version == 2
    assert not store.get_watch(rule)["baseline_ready"]
    assert store.finish_watch(rule, ["123"]) == []


def test_csv_has_separate_qualification_and_preference_columns(tmp_path):
    store = Store(tmp_path / "jobs.sqlite3")
    run = store.start_run("manual", "AI", store.get_profile(), 1)
    store.save_posting(sample_post(), sample_detail(), run)
    path = tmp_path / "analysis.csv"
    assert write_csv(export_rows(store, "qualification", {}), path) == 1
    import csv
    with path.open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert "Python" in rows[0]["자격요건"]
    assert "AWS" in rows[0]["우대사항"]
    assert "AWS" not in rows[0]["자격요건"]
    assert {"공고등록일", "채용마감일", "마감 표시 원문", "원본 URL"}.issubset(rows[0])


def test_collector_persists_and_watch_uses_registration_sort(tmp_path):
    store = Store(tmp_path / "jobs.sqlite3")
    profiles = []

    class FakeClient:
        def search(self, query, profile, page):
            profiles.append(profile)
            return [sample_post()], 1

        def detail(self, rec_idx):
            return sample_detail()

    collector = Collector(store, FakeClient)
    first = collector.run("AI", 1)
    assert first.status == "success" and first.new_count == 1
    watch_id = store.list_watches()[0]["id"]
    watched = collector.run("AI", 1, watch_id)
    assert watched.alerts == []
    assert watched.status == "success" and watched.failed_count == 0
    assert profiles[-1].sort == "reg_dt"
    assert store.dashboard()["total"] == 1


def test_manual_criteria_are_used_and_snapshotted_without_changing_watch(tmp_path):
    store = Store(tmp_path / "jobs.sqlite3")
    used = []

    class FakeClient:
        def search(self, _query, profile, _page):
            used.append(profile)
            return [sample_post()], 1

        def detail(self, _rec_idx):
            return sample_detail()

    custom = replace(store.get_profile(), location_codes=("102000",),
                     experience_codes=("2",), experience_max=2,
                     education_codes=("8",))
    result = Collector(store, FakeClient).run("AI", 1, profile_override=custom)
    assert result.status == "success" and used[0].criteria() == custom.criteria()
    assert json.loads(store.recent_runs()[0]["profile_snapshot"])["location_codes"] == ["102000"]
    assert store.get_profile().location_codes == ("101000",)
    assert store.list_watches()[0]["profile_version"] == 1
    with pytest.raises(ValueError, match="감시 작업"):
        Collector(store, FakeClient).run("AI", 1, store.list_watches()[0]["id"],
                                         profile_override=custom)


def test_posting_date_and_deadline_sort_keep_unknown_and_expired_last(tmp_path):
    store = Store(tmp_path / "jobs.sqlite3")
    run = store.start_run("manual", "AI", store.get_profile(), 1)
    today = date.today()
    from datetime import timedelta
    values = [
        ("1", today.isoformat(), (today + timedelta(days=2)).isoformat()),
        ("2", (today - timedelta(days=1)).isoformat(), (today + timedelta(days=10)).isoformat()),
        ("3", "", ""),
        ("4", (today - timedelta(days=2)).isoformat(), (today - timedelta(days=1)).isoformat()),
    ]
    for rec_idx, posted, deadline in values:
        store.save_posting(replace(sample_post(rec_idx), posted_date=posted,
                                   deadline_date=deadline), sample_detail(), run)
    ids = lambda sort: [item["rec_idx"] for item in store.list_postings(sort=sort)["items"]]
    assert ids("posted_newest") == ["1", "2", "4", "3"]
    assert ids("posted_oldest") == ["4", "2", "1", "3"]
    assert ids("deadline_soon") == ["1", "2", "4", "3"]
    assert ids("deadline_late") == ["2", "1", "4", "3"]
    store.save_posting(replace(sample_post("1"), posted_date="", updated_date=today.isoformat(),
                               deadline_date=""), Detail(status="failed"), run)
    item = store.get_posting("1")
    assert item["posted_date"] == today.isoformat() and item["updated_date"] == today.isoformat()
    assert item["deadline_date"] == ""


def test_analysis_keyword_filter_uses_selected_section(tmp_path):
    store = Store(tmp_path / "jobs.sqlite3")
    run = store.start_run("manual", "AI", store.get_profile(), 1)
    store.save_posting(sample_post(), sample_detail(), run)
    assert store.analyze("qualification", {"tech": "Python"})["total"] == 1
    assert store.analyze("qualification", {"tech": "AWS"})["total"] == 0
    assert store.analyze("preference", {"tech": "AWS"})["total"] == 1
    assert store.analyze("preference", {"tech": "Python"})["total"] == 0


def test_education_profile_filters_only_selected_levels():
    html = """<div class='item_recruit'><strong class='corp_name'>회사</strong>
      <h2 class='job_tit'><a href='/zf_user/jobs/relay/view?rec_idx=456' title='AI 엔지니어'>AI</a></h2>
      <div class='job_condition'><span>서울</span><span>신입</span><span>고졸</span></div>
      <div class='job_sector'>AI·데이터</div></div>"""
    assert len(parse_list(html, "AI", SearchProfile(education_codes=()))[0]) == 1
    assert parse_list(html, "AI", SearchProfile(education_codes=("8",)))[0] == []
    assert valid_education(["신입", "대졸↑"], ("8",))
    assert not valid_education(["신입", "초대졸↑"], ("8",))
    assert not valid_education(["경력무관", "고졸"], ("0",))


def test_collector_watch_baseline_then_new_post_and_history(tmp_path):
    store = Store(tmp_path / "jobs.sqlite3")
    rule = store.list_watches()[0]["id"]
    calls = {"count": 0}

    class FakeClient:
        def search(self, _query, _profile, _page):
            calls["count"] += 1
            jobs = [sample_post()]
            if calls["count"] > 1:
                jobs.append(sample_post("456"))
            return jobs, len(jobs)

        def detail(self, _rec_idx):
            return sample_detail()

    collector = Collector(store, FakeClient)
    assert collector.run("AI", 1, rule).alerts == []
    second = collector.run("AI", 1, rule)
    assert len(second.alerts) == 1
    assert second.alerts[0]["posting_id"] == "456"
    assert collector.run("AI", 1, rule).alerts == []
    store.delete_watch(rule)
    assert len(store.alerts()) == 1


def test_failed_watch_does_not_establish_baseline(tmp_path):
    store = Store(tmp_path / "jobs.sqlite3")
    rule = store.list_watches()[0]["id"]

    class FailingClient:
        def search(self, *_args):
            raise CrawlError("일시적인 접근 오류")

    result = Collector(store, FailingClient).run("AI", 1, rule)
    assert result.status == "failed"
    assert not store.get_watch(rule)["baseline_ready"]
    assert store.alerts() == []


def test_fresh_install_starts_ai_watch_once_and_respects_deletion(tmp_path):
    path = tmp_path / "jobs.sqlite3"
    store = Store(path)
    profile = store.get_profile()
    assert profile.location_codes == ("101000",)
    assert profile.experience_codes == ("1", "2") and profile.experience_max == 3
    assert profile.education_codes == ("0", "8")
    watches = store.list_watches()
    assert len(watches) == 1
    assert watches[0]["query"] == "AI" and watches[0]["interval_minutes"] == 60
    assert watches[0]["enabled"] and not watches[0]["baseline_ready"]
    assert len(Store(path).list_watches()) == 1
    with pytest.raises(ValueError, match="이미 감시 중인 검색어"):
        store.add_watch("ai", 60)
    store.delete_watch(watches[0]["id"])
    assert Store(path).list_watches() == []


def test_upgrade_from_empty_v1_adds_default_ai_watch(tmp_path):
    path = tmp_path / "jobs.sqlite3"
    store = Store(path)
    store.delete_watch(store.list_watches()[0]["id"])
    with sqlite3.connect(path) as con:
        con.execute("DELETE FROM schema_version WHERE version=2")
        con.execute("PRAGMA user_version=1")
    watches = Store(path).list_watches()
    assert len(watches) == 1 and watches[0]["query"] == "AI"


def test_upgrade_keeps_existing_custom_watch(tmp_path):
    path = tmp_path / "jobs.sqlite3"
    store = Store(path)
    store.delete_watch(store.list_watches()[0]["id"])
    custom = store.add_watch("백엔드", 120)
    with sqlite3.connect(path) as con:
        con.execute("DELETE FROM schema_version WHERE version=2")
        con.execute("PRAGMA user_version=1")
    reopened = Store(path)
    watches = reopened.list_watches()
    assert {item["query"] for item in watches} == {"백엔드", "AI"}
    assert reopened.get_watch(custom)["interval_minutes"] == 120
    with sqlite3.connect(path) as con:
        assert con.execute("PRAGMA user_version").fetchone()[0] == 6


def test_upgrade_corrects_old_education_code_and_resets_baseline(tmp_path):
    path = tmp_path / "jobs.sqlite3"
    store = Store(path)
    rule = store.list_watches()[0]["id"]
    run = store.start_run("manual", "AI", store.get_profile(), 1)
    store.save_posting(sample_post(), sample_detail(), run)
    store.finish_watch(rule, ["123"])
    with sqlite3.connect(path) as con:
        old = store.get_profile()
        import json
        criteria = old.criteria()
        criteria["education_codes"] = ["0", "4"]
        con.execute("UPDATE search_profiles SET criteria_json=? WHERE id=1",
                    (json.dumps(criteria),))
        con.execute("DELETE FROM schema_version WHERE version=3")
        con.execute("PRAGMA user_version=2")
    upgraded = Store(path)
    assert upgraded.get_profile().education_codes == ("0", "8")
    assert upgraded.get_profile().version == old.version + 1
    assert not upgraded.get_watch(rule)["baseline_ready"]
    with sqlite3.connect(path) as con:
        assert con.execute("SELECT COUNT(*) FROM watch_seen").fetchone()[0] == 0


def test_v3_database_adds_date_columns_without_losing_postings(tmp_path):
    path = tmp_path / "legacy.sqlite3"
    with sqlite3.connect(path) as con:
        con.execute("""CREATE TABLE postings (
            rec_idx TEXT PRIMARY KEY, company TEXT NOT NULL, title TEXT NOT NULL,
            url TEXT NOT NULL, sector TEXT NOT NULL DEFAULT '',
            career TEXT NOT NULL DEFAULT '', education TEXT NOT NULL DEFAULT '',
            conditions TEXT NOT NULL DEFAULT '', deadline TEXT NOT NULL DEFAULT '',
            full_text TEXT NOT NULL DEFAULT '', detail_status TEXT NOT NULL DEFAULT 'pending',
            first_seen_at TEXT NOT NULL, last_seen_at TEXT NOT NULL)""")
        con.execute("CREATE TABLE schema_version(version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)")
        con.execute("""INSERT INTO postings(rec_idx,company,title,url,first_seen_at,last_seen_at)
                       VALUES ('123','회사','AI 개발자','https://www.saramin.co.kr/job/123','old','old')""")
        con.execute("PRAGMA user_version=3")
    Store(path)
    with sqlite3.connect(path) as con:
        con.row_factory = sqlite3.Row
        row = con.execute("SELECT * FROM postings WHERE rec_idx='123'").fetchone()
        assert row["title"] == "AI 개발자" and row["posted_date"] == ""
        assert row["deadline_date"] == "" and row["last_seen_at"] == "old"
        assert con.execute("PRAGMA user_version").fetchone()[0] == 6


def test_custom_profile_changes_request_and_resets_watch_safely(tmp_path):
    store = Store(tmp_path / "jobs.sqlite3")
    rule = store.list_watches()[0]["id"]
    old = store.get_profile()
    changed = store.save_profile(replace(
        old, location_codes=("102000", "108000"), experience_codes=("2",),
        experience_max=5, education_codes=("8",)))
    assert changed.version == old.version + 1
    assert store.save_profile(changed).version == changed.version
    assert search_params("AI", changed, 1)["loc_mcd"] == "102000,108000"
    assert search_params("AI", changed, 1)["exp_cd"] == "2"
    assert search_params("AI", changed, 1)["edu_cd"] == "8"
    assert not store.get_watch(rule)["baseline_ready"]
    assert store.finish_watch(rule, [], expected_generation=0,
                              expected_profile_version=old.version) == []
    assert not store.get_watch(rule)["baseline_ready"]
    with pytest.raises(ValueError):
        store.save_profile(replace(changed, location_codes=("999999",)))


def test_run_comparison_separates_discovery_registration_change_and_closure(tmp_path):
    store = Store(tmp_path / "comparison.sqlite3")
    phase = {"number": 0, "closed_checks": []}
    next_day = (date.today() + timedelta(days=1)).isoformat()

    class FakeClient:
        def search(self, _query, _profile, _page):
            phase["number"] += 1
            if phase["number"] == 1:
                jobs = [sample_post("1"), sample_post("2"), sample_post("3")]
            else:
                jobs = [sample_post("1"), sample_post("2"),
                        replace(sample_post("4"), posted_date=next_day)]
            return jobs, len(jobs)

        def detail(self, rec_idx):
            detail = sample_detail()
            if rec_idx == "2" and phase["number"] >= 2:
                return replace(detail, full_text=detail.full_text + "\n수정된 상세 문구")
            return detail

        def is_closed(self, rec_idx):
            phase["closed_checks"].append(rec_idx)
            return rec_idx == "3"

    collector = Collector(store, FakeClient)
    first = collector.run("AI", 1)
    assert first.discovered_count is None and first.new_count == 3
    second = collector.run("ai", 1)
    assert (second.new_count, second.updated_count) == (1, 2)
    assert (second.discovered_count, second.registered_count, second.changed_count,
            second.missing_count, second.closed_count) == (1, 1, 1, 1, 1)
    assert {(row["kind"], row["posting_id"]) for row in store.run_events(second.run_id)} == {
        ("discovered", "4"), ("registered", "4"), ("changed", "2"),
        ("missing", "3"), ("closed", "3")}
    third = collector.run("AI", 1)
    assert (third.discovered_count, third.changed_count, third.missing_count) == (0, 0, 0)
    assert phase["closed_checks"] == ["3"]


def test_failed_listing_cannot_claim_missing_or_closed(tmp_path):
    store = Store(tmp_path / "partial.sqlite3")
    phase = {"number": 0, "closed": 0}

    class FakeClient:
        def search(self, _query, _profile, page):
            if page == 1:
                phase["number"] += 1
                return ([sample_post("1")], 1) if phase["number"] == 1 else ([sample_post("2")], 40)
            raise CrawlError("목록 차단")

        def detail(self, _rec_idx):
            return sample_detail()

        def is_closed(self, _rec_idx):
            phase["closed"] += 1
            return True

    collector = Collector(store, FakeClient)
    assert collector.run("AI", 3).status == "success"
    partial = collector.run("AI", 3)
    assert partial.status == "partial"
    assert partial.missing_count is None and partial.closed_count is None
    assert store.run_events(partial.run_id) == [] and phase["closed"] == 0


def test_v4_history_preserved_and_does_not_count_as_comparison(tmp_path):
    path = tmp_path / "existing.sqlite3"
    store = Store(path)
    run = store.start_run("manual", "AI", store.get_profile(), 1)
    store.save_posting(sample_post(), sample_detail(), run)
    store.finish_run(run, "success", 1, 0, 0)
    with sqlite3.connect(path) as con:
        con.execute("UPDATE crawl_runs SET comparison_ready=0 WHERE id=?", (run,))
        con.execute("UPDATE crawl_run_postings SET snapshot_json='' WHERE run_id=?", (run,))
        con.execute("PRAGMA user_version=4")
    reopened = Store(path)
    assert reopened.dashboard()["total"] == 1
    assert reopened.comparable_run("AI", reopened.get_profile(), 1) is None
    assert reopened.recent_runs()[0]["new_count"] == 1


def test_bridge_emits_one_summary_for_multiple_alert_rows(tmp_path):
    pytest.importorskip("PySide6")
    from PySide6.QtCore import QCoreApplication
    from saramin_finder.ui.bridge import Bridge
    from saramin_finder.usecases.collect import CollectResult

    app = QCoreApplication.instance() or QCoreApplication([])
    notices, events = [], []
    bridge = Bridge(Store(tmp_path / "bridge.sqlite3"), notify=notices.append)
    bridge.jobEvent.connect(events.append)
    result = CollectResult(1, query="AI", source="watch", alerts=[{"id": 1}, {"id": 2}],
                           discovered_count=2, registered_count=1, changed_count=0,
                           missing_count=0, closed_count=0)
    bridge._finished(result)
    assert len(notices) == len(events) == 1
    assert "새로 발견 2건" in notices[0]["message"]
    assert bridge.timer.isActive() and bridge.active_watches == set()
    assert app is not None


def test_failed_watch_respects_configured_interval(tmp_path):
    from datetime import datetime, timezone
    store = Store(tmp_path / "retry.sqlite3")
    rule_id = store.list_watches()[0]["id"]
    store.update_watch(rule_id, "AI", 17)
    before = datetime.now(timezone.utc)
    store.fail_watch(rule_id, "일시적인 오류")
    after = datetime.fromisoformat(store.get_watch(rule_id)["next_due_at"])
    assert timedelta(minutes=16, seconds=58) <= after - before <= timedelta(minutes=17, seconds=2)
