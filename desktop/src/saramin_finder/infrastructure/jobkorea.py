from __future__ import annotations

import json
import re
from datetime import datetime
from html import unescape
from urllib.parse import parse_qs, urljoin, urlsplit

from bs4 import BeautifulSoup

from saramin_finder.domain.models import Detail, Posting, SearchProfile
from saramin_finder.domain.rules import (
    GAMEJOB_POSTING_URL, REGION_OPTIONS, extract_sections, gamejob_posting_id, valid_job,
)
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
        if not isinstance(item, dict):
            raise CrawlError("잡코리아 검색 결과의 공고 구조를 읽지 못했습니다.")
        job_id = str(item.get("id", ""))
        if not re.fullmatch(r"[0-9]+", job_id) or not item.get("title"):
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
        url = (f"{GAMEJOB_POSTING_URL}?GI_No={job_id}" if item.get("userRefType") == "G"
               else f"{ORIGINAL_URL}/{job_id}")
        jobs.append(Posting(
            f"jobkorea:{job_id}", unescape(item.get("postingCompanyName") or "정보 없음"),
            title, url, sector, career, education, conditions,
            "상시채용" if ongoing else deadline, iso_date(item.get("createdAt")),
            iso_date(item.get("updatedAt")), "" if ongoing else deadline, provider="jobkorea",
        ))
    return jobs, page < data["totalPages"]


def parse_jobkorea_detail(html: str) -> Detail:
    target = BeautifulSoup(html, "html.parser").select_one("#detail-content")
    return parse_detail(str(target)) if target is not None else Detail()


def gamejob_heading(text: str) -> str | None:
    compact = "".join(text.split()).strip("[]:：.")
    if compact in ("주요업무", "담당업무") or compact.endswith("미션을소개합니다"):
        return "주요업무"
    if (compact in ("자격조건", "자격요건", "지원자격", "필수요건")
            or compact.endswith(("(필수요건)", "(자격요건)"))):
        return "자격요건"
    if (compact in ("우대사항", "우대조건", "우대요건")
            or compact.endswith(("(우대요건)", "(우대사항)"))):
        return "우대사항"
    return None


def parse_gamejob_detail(work_html: str, qualification_html: str) -> Detail:
    bodies = []
    section_lines = []
    has_image = False
    for html, label in ((work_html, "주요업무"), (qualification_html, "자격요건")):
        soup = BeautifulSoup(html, "html.parser")
        body = soup.body or soup
        for tag in body.select("script,style,noscript"):
            tag.decompose()
        has_image |= body.find("img") is not None
        text = body.get_text("\n", strip=True)
        if not text or text == "-":
            continue
        bodies.append(text)
        section_lines.append(label)
        for heading in body.select("th,h1,h2,h3,h4,h5,h6"):
            # Unknown headings end the preceding section, such as application instructions.
            heading.replace_with(gamejob_heading(heading.get_text(" ", strip=True)) or "전형절차")
        section_lines.extend(gamejob_heading(line) or line
                             for line in body.get_text("\n", strip=True).splitlines())
    full_text = "\n".join(bodies)
    if not full_text:
        if has_image:
            return Detail(status="image_only", section_status={
                kind: "image_only" for kind in ("main_work", "qualification", "preference")
            })
        return Detail()
    sections, statuses = extract_sections("\n".join(section_lines))
    return Detail(full_text=full_text, sections=sections, section_status=statuses, status="complete")


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

    def detail(self, posting: Posting) -> Detail:
        job_id = posting.rec_idx.removeprefix("jobkorea:")
        try:
            gamejob_id = gamejob_posting_id(posting.url)
            if gamejob_id:
                return self._gamejob_detail(posting.url, gamejob_id) if gamejob_id == job_id else Detail()
            return parse_jobkorea_detail(self._get(DETAIL_URL, {
                "Gno": job_id,
                "isHiringCenter": "false",
                "hideMapView": "false",
            }))
        except CrawlError:
            return Detail()

    def _gamejob_detail(self, url: str, job_id: str) -> Detail:
        page = BeautifulSoup(self._get(url, {}, allow_redirects=False), "html.parser")
        work = self._gamejob_frame(page, "GI_Work_Content", "GI_Read_Comt_Ifrm", url, job_id)
        qualification = self._gamejob_frame(page, "GI_Comment", "GI_Read_GI_Comment_Ifrm", url, job_id)
        return parse_gamejob_detail(work, qualification)

    def _gamejob_frame(self, page: BeautifulSoup, frame_id: str, endpoint: str,
                       origin: str, job_id: str) -> str:
        frame = page.select_one(f"iframe#{frame_id}[src]")
        if frame is None:
            return ""
        try:
            target = urlsplit(urljoin(origin, frame["src"]))
        except ValueError as exc:
            raise CrawlError("게임잡 상세 주소를 읽지 못했습니다.") from exc
        if (target.scheme != "https" or target.netloc != urlsplit(origin).netloc
                or target.path.casefold() != f"/Recruit/{endpoint}".casefold()
                or parse_qs(target.query, keep_blank_values=True).get("gno") != [job_id]):
            raise CrawlError("게임잡 상세 주소가 공고와 일치하지 않습니다.")
        return self._get(target.geturl(), {}, allow_redirects=False)

    def is_closed(self, rec_idx: str, url: str) -> bool:
        if gamejob_posting_id(url):
            return False
        try:
            return explicit_closure(self._get(f"{ORIGINAL_URL}/{rec_idx.removeprefix('jobkorea:')}", {}))
        except CrawlError:
            return False
