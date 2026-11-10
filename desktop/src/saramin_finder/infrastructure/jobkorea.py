from __future__ import annotations

import json
import re
from datetime import datetime
from html import unescape

from bs4 import BeautifulSoup

from saramin_finder.domain.models import Detail, Posting, SearchProfile
from saramin_finder.domain.rules import REGION_OPTIONS, valid_job
from saramin_finder.infrastructure.saramin import CrawlError, HtmlClient, parse_detail

HOST = "www.jobkorea.co.kr"
ROOT_URL = f"https://{HOST}"
SEARCH_URL = f"{ROOT_URL}/Search/"
ORIGINAL_URL = f"{ROOT_URL}/Recruit/GI_Read"
DETAIL_URL = f"{ROOT_URL}/Recruit/GI_Read_Comt_Ifrm"
PAGE_SIZE = 20
REGION_CODES = {
    "101000": ("I000",), "102000": ("B000",), "108000": ("K000",),
    "103000": ("L230", "L240", "L250", "L260", "L270"),
    "104000": ("F000",), "105000": ("G000",), "106000": ("H000",),
    "107000": ("J000",), "109000": ("A000",), "110000": ("C000",),
    "111000": ("D000",), "112000": ("L000",), "113000": ("M000",),
    "114000": ("P000",), "115000": ("O000",), "116000": ("N000",), "118000": ("1000",),
}
REGION_LABELS = dict(REGION_OPTIONS)
EDUCATION_LABELS = {
    "0": "학력무관", "3": "고졸↑", "4": "초대졸↑", "5": "대졸↑", "6": "석사↑", "7": "박사↑",
}
CAREER_LABELS = {"1": "신입", "2": "경력", "3": "신입·경력", "4": "경력무관"}
FLIGHT_CHUNK = re.compile(r'self\.__next_f\.push\(\[1,("(?:\\.|[^"\\])*")\]\)')
QUERY_RECORD = re.compile(r'\{"dehydratedAt":')


def search_params(query: str, profile: SearchProfile, page: int) -> dict[str, str]:
    if len(query) > 30:
        raise ValueError("잡코리아 검색어는 30자까지 입력할 수 있습니다.")
    params = {"stext": query, "Page_No": str(page),
              "ord": "RegDtDesc" if profile.sort == "reg_dt" else "RelevanceDesc"}
    if profile.experience_codes:
        params["careerType"] = ",".join(profile.experience_codes)
    if profile.experience_max is not None:
        params["careerMax"] = str(profile.experience_max)
    if profile.education_codes:
        education_codes = ["0"] if "0" in profile.education_codes else []
        if "8" in profile.education_codes:
            education_codes.extend(("5", "6", "7"))
        params["edu"] = ",".join(education_codes)
    return params


def listing_data(html: str, query: str, page: int, sort: str) -> dict:
    """Read the search results embedded in the public page, excluding ad cards."""
    try:
        payload = "".join(json.loads(match[1]) for match in FLIGHT_CHUNK.finditer(html))
        decoder = json.JSONDecoder()
        order = "2" if sort == "reg_dt" else "1"
        for match in QUERY_RECORD.finditer(payload):
            record, _ = decoder.raw_decode(payload, match.start())
            key = record.get("queryKey", [])
            if key[:6] != ["JOB_LIST", PAGE_SIZE, page - 1, order, "DESC", query]:
                continue
            data = record["state"]["data"]
            if (data["pageNumber"] == page - 1 and data["pageSize"] == PAGE_SIZE and
                    isinstance(data["content"], list) and
                    len(data["content"]) == min(PAGE_SIZE, max(0, data["totalElements"] - (page - 1) * PAGE_SIZE))):
                return data
    except (TypeError, KeyError, ValueError) as exc:
        raise CrawlError("잡코리아 검색 결과를 읽지 못했습니다.") from exc
    raise CrawlError("잡코리아 검색 결과를 읽지 못했습니다. 사이트 화면 변경 또는 접근 제한을 확인해 주세요.")


def iso_date(value: str | None) -> str:
    try:
        return datetime.fromisoformat(value).date().isoformat() if value else ""
    except (TypeError, ValueError):
        return ""


def region_matches(areas: list[str], regions: tuple[str, ...]) -> bool:
    return any(area.startswith(region.removesuffix("000")) for area in areas for region in regions)


def parse_list(html: str, query: str, profile: SearchProfile, page: int) -> tuple[list[Posting], bool]:
    data = listing_data(html, query, page, profile.sort)
    regions = tuple(region for code in profile.location_codes for region in REGION_CODES[code])
    jobs = []
    for item in data["content"]:
        if not isinstance(item, dict) or not str(item.get("id", "")).isdigit() or not item.get("title"):
            raise CrawlError("잡코리아 검색 결과의 공고 번호나 제목이 누락되었습니다.")
        areas = item.get("areaCodeList") or []
        if regions and not region_matches(areas, regions):
            continue
        title = unescape(item["title"]).strip()
        sector = unescape(item.get("jobClassificationOrIndustry") or "").strip(", ")
        if not valid_job(sector, title, query):
            continue
        career_type = item.get("careerType")
        years = item.get("careerRange")
        career = CAREER_LABELS.get(career_type, "")
        if career_type in ("2", "3") and isinstance(years, int) and 0 < years < 100:
            career += f" {years}년↑"
        education = EDUCATION_LABELS.get(item.get("educationCode"), "")
        deadline = iso_date((item.get("applicationPeriod") or {}).get("end"))
        ongoing = bool(deadline and deadline >= "2070-01-01")
        locations = [REGION_LABELS[code] for code, region in REGION_CODES.items()
                     if region_matches(areas, region) and
                     (code != "112000" or any(area.startswith("L") and
                                              area not in REGION_CODES["103000"] for area in areas))]
        conditions = ", ".join(dict.fromkeys(value for value in (*locations, career, education) if value))
        job_id = str(item["id"])
        jobs.append(Posting(
            f"jobkorea:{job_id}", unescape(item.get("postingCompanyName") or "정보 없음"),
            title, f"{ORIGINAL_URL}/{job_id}", sector, career, education, conditions,
            "상시채용" if ongoing else deadline, iso_date(item.get("createdAt")),
            iso_date(item.get("updatedAt")), "" if ongoing else deadline, provider="jobkorea",
        ))
    return jobs, page < data["totalPages"]


def parse_jobkorea_detail(html: str) -> Detail:
    target = BeautifulSoup(html, "html.parser").select_one("#detail-content")
    return parse_detail(str(target)) if target is not None else Detail()


def explicit_closure(html: str) -> bool:
    timer = BeautifulSoup(html, "html.parser").select_one('[data-sentry-component="ApplyTimerBox"]')
    return timer is not None and "마감되었습니다." in timer.stripped_strings


class JobKoreaClient(HtmlClient):
    user_agent = "SaraminAIFinder/1.0 (local job search)"

    def search(self, query: str, profile: SearchProfile, page: int) -> tuple[list[Posting], bool]:
        params = search_params(query, profile, page)
        # The public search UI stores selected regions in this preference cookie.
        regions = ",".join(dict.fromkeys(
            region for code in profile.location_codes for region in REGION_CODES[code]))
        self.session.cookies.set("searchBarLocal", regions, domain=HOST, path="/")
        return parse_list(self._get(SEARCH_URL, params), query, profile, page)

    def detail(self, rec_idx: str) -> Detail:
        try:
            return parse_jobkorea_detail(self._get(DETAIL_URL, {
                "Gno": rec_idx.removeprefix("jobkorea:"),
                "isHiringCenter": "false",
                "hideMapView": "false",
            }))
        except CrawlError:
            return Detail()

    def is_closed(self, rec_idx: str) -> bool:
        try:
            return explicit_closure(self._get(f"{ORIGINAL_URL}/{rec_idx.removeprefix('jobkorea:')}", {}))
        except CrawlError:
            return False
