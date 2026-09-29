from __future__ import annotations

import re
import random
import time
from datetime import date, datetime, timedelta, timezone
from urllib.parse import parse_qs, urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from saramin_finder.domain.models import Detail, Posting, SearchProfile
from saramin_finder.domain.rules import extract_sections, valid_education, valid_job

SEARCH_URL = "https://www.saramin.co.kr/zf_user/search/recruit"
DETAIL_URL = "https://www.saramin.co.kr/zf_user/jobs/relay/view-detail"
ORIGINAL_URL = "https://www.saramin.co.kr/zf_user/jobs/view"
ROOT_URL = "https://www.saramin.co.kr"
USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")


class CrawlError(RuntimeError):
    pass


def listing_dates(label: str) -> tuple[str, str]:
    """Keep registration and modification dates distinct."""
    match = re.search(r"(등록일|수정일)\s*(\d{2,4})[./-](\d{1,2})[./-](\d{1,2})", label)
    if not match:
        return "", ""
    kind, year, month, day = match.groups()
    year = int(year) + (2000 if len(year) == 2 else 0)
    try:
        value = date(year, int(month), int(day)).isoformat()
    except ValueError:
        return "", ""
    return (value, "") if kind == "등록일" else ("", value)


def deadline_date(label: str, today: date | None = None) -> str:
    """Infer the next occurrence when a listing shows only month and day."""
    today = today or datetime.now(timezone(timedelta(hours=9))).date()
    if "오늘마감" in label:
        return today.isoformat()
    if "내일마감" in label:
        return (today + timedelta(days=1)).isoformat()
    match = re.search(r"(?<!\d)(?:(\d{4})[./-])?(\d{1,2})[./-](\d{1,2})(?!\d)", label)
    if not match:
        return ""
    year, month, day = match.groups()
    try:
        inferred = date(int(year) if year else today.year, int(month), int(day))
        if not year and inferred < today:
            inferred = date(today.year + 1, int(month), int(day))
        return inferred.isoformat()
    except ValueError:
        return ""


def search_params(query: str, profile: SearchProfile, page: int) -> dict[str, str]:
    criteria = profile.criteria()
    params = {
        "searchword": query,
        "recruitPage": str(page),
        "recruitPageCount": "40",
        "recruitSort": criteria["sort"],
    }
    if criteria["location_codes"]:
        params["loc_mcd"] = ",".join(criteria["location_codes"])
    if criteria["experience_codes"]:
        params["exp_cd"] = ",".join(criteria["experience_codes"])
    if criteria["experience_max"] is not None:
        params["exp_max"] = str(criteria["experience_max"])
    if criteria["education_codes"]:
        params["edu_cd"] = ",".join(criteria["education_codes"])
    return params


def parse_list(html: str, query: str, profile: SearchProfile | None = None) -> tuple[list[Posting], int]:
    soup = BeautifulSoup(html, "html.parser")
    if re.search(r"총\s*0건의\s*검색결과", soup.title.get_text(" ", strip=True) if soup.title else ""):
        return [], 0
    elements = soup.select("div.item_recruit")
    if not elements:
        visible = soup.get_text(" ", strip=True)
        if any(marker in visible for marker in ("검색 결과가 없습니다", "검색결과가 없습니다",
                                                "검색 결과 없음", "검색된 공고가 없습니다")):
            return [], 0
        raise CrawlError("검색 결과 구조를 읽지 못했습니다. 사이트 화면 변경 또는 접근 제한을 확인해 주세요.")
    jobs: list[Posting] = []
    for element in elements:
        anchor = element.select_one("h2.job_tit a")
        if anchor is None:
            continue
        href = anchor.get("href", "")
        parsed_url = urlparse(urljoin(ROOT_URL, href))
        if parsed_url.scheme != "https" or parsed_url.netloc != "www.saramin.co.kr":
            continue
        rec_idx = parse_qs(parsed_url.query).get("rec_idx", [""])[0]
        if not rec_idx.isdigit():
            continue
        title = (anchor.get("title") or anchor.get_text(" ", strip=True)).strip()
        company_tag = element.select_one("strong.corp_name")
        company = company_tag.get_text(" ", strip=True) if company_tag else "정보 없음"
        condition_tag = element.select_one("div.job_condition")
        conditions = [x.get_text(" ", strip=True) for x in condition_tag.select("span")] if condition_tag else []
        sector_tag = element.select_one("div.job_sector")
        date_tag = sector_tag.select_one("span.job_day") if sector_tag else None
        posted_date, updated_date = listing_dates(date_tag.get_text(" ", strip=True) if date_tag else "")
        if sector_tag:
            for hidden in sector_tag.select("span.job_day"):
                hidden.decompose()
        sector = sector_tag.get_text(" ", strip=True) if sector_tag else ""
        deadline_tag = element.select_one("div.job_date span.date")
        deadline = deadline_tag.get_text(" ", strip=True) if deadline_tag else ""
        education_codes = profile.education_codes if profile else ("0", "8")
        if not valid_education(conditions, education_codes) or not valid_job(sector, title, query):
            continue
        career = next((x for x in conditions if "신입" in x or "경력" in x), "")
        education = next((x for x in conditions if "학력" in x or "대졸" in x or "대학교" in x), "")
        jobs.append(Posting(rec_idx, company, title, urljoin(ROOT_URL, href), sector,
                            career, education, ", ".join(conditions), deadline,
                            posted_date, updated_date, deadline_date(deadline)))
    return jobs, len(elements)


def parse_detail(html: str) -> Detail:
    soup = BeautifulSoup(html, "html.parser")
    target = soup.select_one(".user_content") or soup.body or soup
    for element in target.select("script,style,noscript"):
        element.decompose()
    lines = [" ".join(line.split()) for line in target.get_text("\n", strip=True).splitlines()]
    full_text = "\n".join(line for line in lines if line)
    if len(full_text) < 100 and target.select_one("img"):
        return Detail(status="image_only", section_status={k: "image_only" for k in
                      ("main_work", "qualification", "preference")})
    if not full_text:
        return Detail(status="failed")
    sections, statuses = extract_sections(full_text)
    return Detail(full_text=full_text, sections=sections, section_status=statuses,
                  status="complete")


def explicit_closure(html: str) -> bool:
    """Accept only an explicit site closure message outside the employer's job body."""
    soup = BeautifulSoup(html, "html.parser")
    for node in soup.find_all(string=re.compile(r"본 채용정보는 마감되었습니다|채용공고가 마감되었습니다")):
        if node.find_parent(class_="user_content"):
            continue
        if node.find_parent(("script", "style", "noscript")):
            continue
        return True
    return False


class SaraminClient:
    def __init__(self, session: requests.Session | None = None,
                 delay_range: tuple[float, float] = (0.5, 1.0)):
        self.session = session or requests.Session()
        self.session.headers.update({
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8",
        })
        self.delay_range = delay_range
        self._requested = False

    def _get(self, url: str, params: dict[str, str]) -> str:
        last_error: Exception | None = None
        for attempt in range(2):
            if self._requested:
                time.sleep(random.uniform(*self.delay_range))
            self._requested = True
            try:
                response = self.session.get(url, params=params, timeout=12)
                response.raise_for_status()
                if re.search(r"HTTP_BAD_REQUEST\.php|captcha", response.text, re.IGNORECASE):
                    raise CrawlError("사이트가 요청을 거부했습니다.")
                return response.text
            except (requests.RequestException, CrawlError) as exc:
                last_error = exc
                if attempt == 0:
                    time.sleep(1)
        raise CrawlError(f"요청 실패: {last_error}")

    def search(self, query: str, profile: SearchProfile, page: int) -> tuple[list[Posting], int]:
        return parse_list(self._get(SEARCH_URL, search_params(query, profile, page)), query, profile)

    def detail(self, rec_idx: str) -> Detail:
        try:
            return parse_detail(self._get(DETAIL_URL, {"rec_idx": rec_idx}))
        except CrawlError:
            return Detail(status="failed")

    def is_closed(self, rec_idx: str) -> bool:
        try:
            return explicit_closure(self._get(ORIGINAL_URL, {"rec_idx": rec_idx}))
        except CrawlError:
            return False
