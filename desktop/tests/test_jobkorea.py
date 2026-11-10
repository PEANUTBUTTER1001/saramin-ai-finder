import json
from dataclasses import replace

import pytest

from saramin_finder.domain.models import SearchProfile
from saramin_finder.domain.rules import gamejob_posting_id
from saramin_finder.infrastructure.jobkorea import (
    CrawlError, JobKoreaClient, explicit_closure, parse_gamejob_detail,
    parse_jobkorea_detail, parse_list, search_params,
)


def listing_html(items, *, page=1, total=None, order="1"):
    count = len(items) if total is None else total
    record = {
        "dehydratedAt": 0,
        "state": {"data": {
            "pageSize": 20, "pageNumber": page - 1, "totalElements": count,
            "totalPages": (count + 19) // 20, "content": items,
        }},
        "queryKey": ["JOB_LIST", 20, page - 1, order, "DESC", "AI"],
    }
    chunk = json.dumps({"queries": [record]})
    return f"<script>self.__next_f.push([1,{json.dumps(chunk)}])</script>"


def test_jobkorea_search_uses_filters_and_reads_site_pagination():
    profile = replace(SearchProfile(), sort="reg_dt")
    assert search_params("AI", profile, 2) == {
        "stext": "AI", "Page_No": "2", "ord": "RegDtDesc",
        "careerType": "1,2", "careerMax": "3", "edu": "0,5,6,7",
    }
    item = {
        "id": "123", "title": "AI 엔지니어", "postingCompanyName": "회사",
        "areaCodeList": ["I150"], "jobClassificationOrIndustry": ",AI·개발,",
        "careerType": "2", "careerRange": 3, "educationCode": "5",
        "createdAt": "2026-11-01T10:30:00+09:00",
        "applicationPeriod": {"end": "2070-01-01T00:00:00+09:00"},
    }
    out_of_region = {**item, "id": "124", "areaCodeList": ["B150"]}
    html = listing_html([item] + [out_of_region] * 19, total=21, order="2")
    jobs, has_more = parse_list(html, "AI", profile, 1)
    assert has_more and len(jobs) == 1
    job = jobs[0]
    assert (job.rec_idx, job.provider, job.career, job.education) == ("jobkorea:123", "jobkorea", "경력 3년↑", "대졸↑")
    assert job.posted_date == "2026-11-01" and job.updated_date == ""
    assert job.deadline == "상시채용" and job.deadline_date == ""
    assert job.url == "https://www.jobkorea.co.kr/Recruit/GI_Read/123"
    assert parse_list(listing_html([out_of_region], page=2, total=21, order="2"),
                      "AI", profile, 2) == ([], False)


def test_jobkorea_distinguishes_empty_from_missing_or_wrong_page():
    profile = SearchProfile()
    assert parse_list(listing_html([]), "AI", profile, 1) == ([], False)
    with pytest.raises(CrawlError):
        parse_list(listing_html([]), "AI", profile, 2)
    with pytest.raises(CrawlError):
        parse_list("<html>일시적으로 접근할 수 없습니다.</html>", "AI", profile, 1)


def test_jobkorea_reads_only_detail_body_and_explicit_site_closure():
    html = """<h1>외부 페이지 문구</h1><div id="detail-content">
        <h3>자격요건</h3><p>Python 경험</p><h3>우대사항</h3><p>Docker 경험</p></div>"""
    detail = parse_jobkorea_detail(html)
    assert detail.status == "complete" and "외부 페이지 문구" not in detail.full_text
    assert detail.sections["qualification"] == "Python 경험"
    assert detail.sections["preference"] == "Docker 경험"
    assert parse_jobkorea_detail('<div id="detail-content"><img src="notice.png"></div>').status == "image_only"
    assert parse_jobkorea_detail("<body>접근 오류</body>").status == "failed"
    assert not explicit_closure("<p>마감되었습니다.</p>")
    assert explicit_closure('<div data-sentry-component="ApplyTimerBox"><span>마감되었습니다.</span></div>')


@pytest.mark.parametrize("job_id", ["280848", "913572"])
def test_gamejob_type_uses_its_own_posting_and_linked_detail(monkeypatch, job_id):
    profile = SearchProfile()
    item = {"id": job_id, "title": "AI 개발자", "areaCodeList": ["I150"], "userRefType": "G"}
    jobs, _ = parse_list(listing_html([item, {**item, "id": "678", "userRefType": "C"}]),
                         "AI", profile, 1)
    gamejob, native = jobs
    origin = f"https://www.gamejob.co.kr/Recruit/GI_Read/View?GI_No={job_id}"
    work_url = f"https://www.gamejob.co.kr/Recruit/GI_Read_Comt_Ifrm?gno={job_id}&v1"
    comment_url = f"https://www.gamejob.co.kr/Recruit/GI_Read_GI_Comment_Ifrm?gno={job_id}&v1"
    assert gamejob.rec_idx == f"jobkorea:{job_id}" and gamejob.provider == "jobkorea"
    assert gamejob.url == origin and gamejob_posting_id(origin) == job_id
    assert native.url == "https://www.jobkorea.co.kr/Recruit/GI_Read/678"
    calls = []

    def get(url, params, *, allow_redirects=True):
        calls.append((url, params, allow_redirects))
        responses = {
            origin: f"""<iframe id="GI_Work_Content" src="/Recruit/GI_Read_Comt_Ifrm?gno={job_id}&amp;v1"></iframe>
                        <iframe id="GI_Comment" src="{comment_url}"></iframe>""",
            work_url: """<table><tr><th>팀과 함께할 미션을 소개합니다.</th></tr><tr><td>AI 서비스 개발</td></tr>
                <tr><th>이런 분을 찾습니다! (필수요건)</th></tr><tr><td>Python 경험</td></tr>
                <tr><th>함께 일하고 싶은 분입니다! (우대요건)</th></tr><tr><td>Docker 운영</td></tr>
                <tr><th>회사 채용 전형 안내</th></tr><tr><td>서류 전형</td></tr></table>""",
            comment_url: "<body>SQL 사용 경험</body>",
            "https://www.jobkorea.co.kr/Recruit/GI_Read_Comt_Ifrm":
                '<div id="detail-content"><h3>자격요건</h3><p>Java 경험</p></div>',
        }
        return responses[url]

    client = JobKoreaClient()
    monkeypatch.setattr(client, "_get", get)
    detail = client.detail(gamejob)
    assert detail.status == "complete"
    assert detail.sections == {"main_work": "AI 서비스 개발",
                               "qualification": "Python 경험\nSQL 사용 경험", "preference": "Docker 운영"}
    assert "서류 전형" in detail.full_text
    assert calls == [(origin, {}, False), (work_url, {}, False), (comment_url, {}, False)]
    assert not client.is_closed(gamejob.rec_idx, gamejob.url) and len(calls) == 3
    assert client.detail(native).sections["qualification"] == "Java 경험"
    assert calls[-1][1]["Gno"] == "678" and calls[-1][2]


@pytest.mark.parametrize("frame_src", [
    "https://example.com/Recruit/GI_Read_Comt_Ifrm?gno=42",
    "/Recruit/GI_Read_Comt_Ifrm?gno=43",
    "/Recruit/Other?gno=42",
])
def test_gamejob_rejects_frame_outside_the_same_posting(monkeypatch, frame_src):
    jobs, _ = parse_list(listing_html([
        {"id": "42", "title": "AI 개발자", "areaCodeList": ["I150"], "userRefType": "G"},
    ]), "AI", SearchProfile(), 1)
    posting = jobs[0]
    client = JobKoreaClient()

    def get(url, _params, *, allow_redirects=True):
        assert url == posting.url and not allow_redirects
        return f'<iframe id="GI_Work_Content" src="{frame_src}"></iframe>'

    monkeypatch.setattr(client, "_get", get)
    assert client.detail(posting).status == "failed"


def test_gamejob_detail_distinguishes_empty_and_image_only():
    assert parse_gamejob_detail("", "<body>-</body>").status == "failed"
    assert parse_gamejob_detail('<img src="notice.png">', "<body>-</body>").status == "image_only"
    assert gamejob_posting_id("http://www.gamejob.co.kr/Recruit/GI_Read/View?GI_No=42") is None
    assert gamejob_posting_id("https://www.gamejob.co.kr/other?GI_No=42") is None
