from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta, timezone
from typing import Callable

from saramin_finder.domain.models import Detail, SearchProfile
from saramin_finder.domain.rules import validate_profile, validate_query
from saramin_finder.infrastructure.database import Store
from saramin_finder.infrastructure.saramin import CrawlError, SaraminClient


Progress = Callable[[dict], None]


@dataclass
class CollectResult:
    run_id: int
    query: str = ""
    source: str = "manual"
    status: str = "success"
    new_count: int = 0
    updated_count: int = 0
    failed_count: int = 0
    posting_ids: list[str] = field(default_factory=list)
    alerts: list[dict] = field(default_factory=list)
    baseline_run_id: int | None = None
    discovered_count: int | None = None
    registered_count: int | None = None
    changed_count: int | None = None
    missing_count: int | None = None
    closed_count: int | None = None
    error: str = ""

    def summary(self) -> dict[str, str]:
        status_label = {"success": "완료", "partial": "일부 완료", "failed": "실패"}[self.status]
        title = f"{self.query} · {'감시 확인' if self.source == 'watch' else '수집'} {status_label}"
        if self.status == "failed":
            message = f"목록 확인 실패 · {self.error or '오류 내용을 확인해 주세요.'}"
        elif self.discovered_count is None:
            prefix = (f"비교 기준 등록 {len(self.posting_ids)}건" if self.status == "success" else
                      "일부 확인 실패 · 비교 지표 미확인")
            message = f"{prefix} · DB 첫 저장 {self.new_count}건 · 상세 실패 {self.failed_count}건"
        else:
            message = (f"새로 발견 {self.discovered_count}건 (등록일로 신규 확인 {self.registered_count}건)"
                       f" · 실제 수정 {self.changed_count}건 · 이번 검색 미검출 {self.missing_count}건"
                       f" (원본 종료 확인 {self.closed_count}건) · 상세 실패 {self.failed_count}건")
        return {"title": title, "message": message}


LIST_FIELDS = ("company", "title", "sector", "career", "education", "conditions",
               "deadline", "posted_date", "updated_date", "deadline_date")


def snapshot(item: dict) -> dict:
    return {key: item[key] for key in (*LIST_FIELDS, "full_text", "detail_status")}


def changed(before: dict, after: dict, detail_ok: bool) -> bool:
    return any(before["values"][key] != after["values"][key] for key in LIST_FIELDS) or (
        before["detail_ok"] and detail_ok and
        any(before["values"][key] != after["values"][key]
            for key in ("full_text", "detail_status")))


class Collector:
    def __init__(self, store: Store, client_factory=SaraminClient):
        self.store = store
        self.client_factory = client_factory

    def run(self, query: str, pages: int = 10, watch_rule_id: int | None = None,
            progress: Progress | None = None,
            profile_override: SearchProfile | None = None) -> CollectResult:
        query = validate_query(query)
        if pages not in (1, 3, 10):
            raise ValueError("조회 페이지는 1, 3, 10 중 선택해 주세요.")
        profile = self.store.get_profile()
        if profile_override is not None:
            if watch_rule_id is not None:
                raise ValueError("수동 수집 조건은 감시 작업에 적용할 수 없습니다.")
            profile = validate_profile(profile_override)
        source = "watch" if watch_rule_id is not None else "manual"
        watch_generation = None
        if watch_rule_id is not None:
            rule = self.store.get_watch(watch_rule_id)
            if not rule or not rule["enabled"] or rule["query"] != query:
                raise ValueError("감시 조건이 변경되었거나 일시정지되었습니다.")
            watch_generation = rule["generation"]
            # Verified on the current search page: recruitSort=reg_dt selects registration order.
            profile = replace(profile, sort="reg_dt")
        baseline = self.store.comparable_run(query, profile, pages)
        previous = self.store.run_snapshots(baseline["id"]) if baseline else {}
        run_id = self.store.start_run(source, query, profile, pages, watch_rule_id)
        result = CollectResult(run_id, query=query, source=source,
                               baseline_run_id=baseline["id"] if baseline else None)
        client = self.client_factory()
        seen = set()
        complete_listing = True
        events: dict[str, set[str]] = {kind: set() for kind in
                                       ("discovered", "registered", "changed", "missing", "closed")}
        try:
            for page in range(1, pages + 1):
                if progress:
                    progress({"stage": "list", "page": page, "pages": pages,
                              "message": f"검색 목록 {page}/{pages}페이지 확인 중"})
                postings, raw_count = client.search(query, profile, page)
                for posting in postings:
                    if posting.rec_idx in seen:
                        continue
                    seen.add(posting.rec_idx)
                    result.posting_ids.append(posting.rec_idx)
                    if progress:
                        progress({"stage": "detail", "count": len(seen),
                                  "message": f"상세 확인: {posting.company} · {posting.title}"})
                    detail = client.detail(posting.rec_idx)
                    if detail.status == "failed":
                        result.failed_count += 1
                    is_new = self.store.save_posting(posting, detail, run_id)
                    result.new_count += int(is_new)
                    result.updated_count += int(not is_new)
                    current = snapshot(self.store.get_posting(posting.rec_idx))
                    detail_ok = detail.status != "failed"
                    self.store.record_snapshot(run_id, posting.rec_idx, current, detail_ok)
                    if baseline:
                        if posting.rec_idx not in previous:
                            events["discovered"].add(posting.rec_idx)
                            previous_day = datetime.fromisoformat(baseline["finished_at"]).astimezone(
                                timezone(timedelta(hours=9))).date().isoformat()
                            if posting.posted_date and posting.posted_date > previous_day:
                                events["registered"].add(posting.rec_idx)
                        elif changed(previous[posting.rec_idx],
                                     {"values": current, "detail_ok": detail_ok}, detail_ok):
                            events["changed"].add(posting.rec_idx)
                if raw_count < 40:
                    break
        except CrawlError as exc:
            result.error = str(exc)
            complete_listing = False
        except Exception as exc:
            result.error = f"예기치 않은 수집 오류: {exc}"
            complete_listing = False
        result.status = ("partial" if result.failed_count else "success") if complete_listing else (
            "partial" if result.posting_ids else "failed")
        if baseline and complete_listing:
            events["missing"] = set(previous) - seen
            for posting_id in events["missing"]:
                if progress:
                    progress({"stage": "closure", "message": f"원본 종료 여부 확인: {posting_id}"})
                if client.is_closed(posting_id):
                    events["closed"].add(posting_id)
            self.store.record_events(run_id, events)
            for kind, attribute in (("discovered", "discovered_count"),
                                    ("registered", "registered_count"),
                                    ("changed", "changed_count"),
                                    ("missing", "missing_count"),
                                    ("closed", "closed_count")):
                setattr(result, attribute, len(events[kind]))
        if watch_rule_id is not None:
            if complete_listing:
                result.alerts = self.store.finish_watch(
                    watch_rule_id, result.posting_ids, watch_generation, profile.version)
            else:
                self.store.fail_watch(watch_rule_id, result.error, watch_generation,
                                      profile.version)
        metrics = {key: getattr(result, key) for key in ("baseline_run_id", "discovered_count",
                   "registered_count", "changed_count", "missing_count", "closed_count")}
        self.store.finish_run(run_id, result.status, result.new_count, result.updated_count,
                              result.failed_count, result.error, metrics)
        if progress:
            progress({"stage": "done", "result": result.__dict__,
                      "message": result.summary()["message"]})
        return result
