from __future__ import annotations

from saramin_finder.domain.models import PROVIDERS
from saramin_finder.infrastructure.database import Store


def export_posting_rows(store: Store, filters: dict, sort: str = "recent"):
    """Export every filtered posting in the same order as the archive table."""
    yield ["번호", "즐겨찾기", "공고 ID", "회사", "제목", "직무 분야", "경력", "학력",
           "조건 원문", "공고등록일", "수정일", "채용마감일", "마감 표시 원문",
           "수집 시각", "최초 감시 수집 시각", "최근 감시 수집 시각", "상세 상태",
           "기술 스택", "자격요건", "우대사항", "검색어", "원본 URL", "출처"]
    page, number = 1, 0
    while True:
        result = store.list_postings(filters, page=page, per_page=100, sort=sort)
        for row in result["items"]:
            item = store.get_posting(row["rec_idx"])
            number += 1
            yield [number, "예" if item["favorite"] else "아니오", item["rec_idx"].split(":")[-1],
                   item["company"], item["title"], item["sector"], item["career"], item["education"],
                   item["conditions"], item["posted_date"], item["updated_date"],
                   item["deadline_date"], item["deadline"], item["last_seen_at"],
                   item["first_watch_collected_at"], item["last_watch_collected_at"],
                   item["detail_status"], ", ".join(row["tech"]),
                   item["sections"].get("qualification", {}).get("text", ""),
                   item["sections"].get("preference", {}).get("text", ""),
                   ", ".join(item["queries"]), item["url"], PROVIDERS[item["provider"]]]
        if page * result["per_page"] >= result["total"]:
            break
        page += 1


def export_rows(store: Store, kind: str, filters: dict):
    """Yield CSV rows without opening files or altering the archive."""
    yield ["공고 ID", "회사", "제목", "직무 분야", "경력", "수집 시각",
           "공고등록일", "채용마감일", "마감 표시 원문",
           "자격요건", "우대사항", "자격요건 키워드", "우대사항 키워드",
           "자격요건 추출 상태", "우대사항 추출 상태", "검색어", "원본 URL", "출처"]
    page = 1
    while True:
        batch = store.analyze(kind, filters, page=page, per_page=500)["items"]
        if not batch:
            break
        for row in batch:
            item = store.get_posting(row["rec_idx"])
            sections = item["sections"]
            keywords = item["keywords"]
            qual = sections.get("qualification", {})
            pref = sections.get("preference", {})
            yield [
                item["rec_idx"].split(":")[-1], item["company"], item["title"], item["sector"],
                item["career"], item["last_seen_at"], item["posted_date"],
                item["deadline_date"], item["deadline"], qual.get("text", ""),
                pref.get("text", ""), ", ".join(keywords["qualification"]),
                ", ".join(keywords["preference"]), qual.get("status", "missing"),
                pref.get("status", "missing"), ", ".join(item["queries"]), item["url"],
                PROVIDERS[item["provider"]],
            ]
        page += 1
