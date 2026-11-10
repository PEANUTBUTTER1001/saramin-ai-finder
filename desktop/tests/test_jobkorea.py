import json
from dataclasses import replace

import pytest

from saramin_finder.domain.models import SearchProfile
from saramin_finder.infrastructure.jobkorea import (
    CrawlError, explicit_closure, parse_jobkorea_detail, parse_list, search_params,
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
