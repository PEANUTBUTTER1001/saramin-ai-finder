from __future__ import annotations

from saramin_finder.infrastructure.database import Store


def export_rows(store: Store, kind: str, filters: dict):
    """Yield CSV rows without opening files or altering the archive."""
    yield ["공고 ID", "회사", "제목", "직무 분야", "경력", "수집 시각",
           "공고등록일", "채용마감일", "마감 표시 원문",
           "자격요건", "우대사항", "자격요건 키워드", "우대사항 키워드",
           "자격요건 추출 상태", "우대사항 추출 상태", "검색어", "원본 URL"]
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
                item["rec_idx"], item["company"], item["title"], item["sector"],
                item["career"], item["last_seen_at"], item["posted_date"],
                item["deadline_date"], item["deadline"], qual.get("text", ""),
                pref.get("text", ""), ", ".join(keywords["qualification"]),
                ", ".join(keywords["preference"]), qual.get("status", "missing"),
                pref.get("status", "missing"), ", ".join(item["queries"]), item["url"],
            ]
        page += 1
