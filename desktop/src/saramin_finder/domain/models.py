from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SearchProfile:
    id: int = 1
    name: str = "기본 검색 조건"
    version: int = 1
    location_codes: tuple[str, ...] = ("101000",)
    experience_codes: tuple[str, ...] = ("1", "2")
    experience_max: int | None = 3
    education_codes: tuple[str, ...] = ("0", "8")
    sort: str = "relation"
    watch_pages: int = 10

    def criteria(self) -> dict:
        return {
            "location_codes": list(self.location_codes),
            "experience_codes": list(self.experience_codes),
            "experience_max": self.experience_max,
            "education_codes": list(self.education_codes),
            "sort": self.sort,
            "watch_pages": self.watch_pages,
        }


@dataclass(frozen=True)
class Posting:
    rec_idx: str
    company: str
    title: str
    url: str
    sector: str = ""
    career: str = ""
    education: str = ""
    conditions: str = ""
    deadline: str = ""
    posted_date: str = ""
    updated_date: str = ""
    deadline_date: str = ""


@dataclass(frozen=True)
class Detail:
    full_text: str = ""
    sections: dict[str, str] = field(default_factory=dict)
    section_status: dict[str, str] = field(default_factory=dict)
    status: str = "failed"
    parser_version: int = 1
