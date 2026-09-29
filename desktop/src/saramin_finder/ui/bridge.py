from __future__ import annotations

import json
import logging
from dataclasses import replace
from pathlib import Path
from urllib.parse import urlparse

from PySide6.QtCore import QObject, QRunnable, QThreadPool, QTimer, QUrl, Signal, Slot
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QFileDialog

from saramin_finder.infrastructure.database import Store
from saramin_finder.domain.models import SearchProfile
from saramin_finder.domain.rules import REGION_OPTIONS, validate_profile
from saramin_finder.infrastructure.csv_export import write_csv
from saramin_finder.usecases.analyze import export_rows
from saramin_finder.usecases.collect import Collector


class WorkerSignals(QObject):
    progress = Signal(dict)
    finished = Signal(object)
    failed = Signal(str)


class CollectWorker(QRunnable):
    def __init__(self, collector: Collector, query: str, pages: int, watch_rule_id: int | None,
                 profile_override: SearchProfile | None = None):
        super().__init__()
        self.collector = collector
        self.query = query
        self.pages = pages
        self.watch_rule_id = watch_rule_id
        rule = collector.store.get_watch(watch_rule_id) if watch_rule_id is not None else None
        self.watch_generation = rule["generation"] if rule else None
        self.watch_profile_version = rule["profile_version"] if rule else None
        self.profile_override = profile_override
        self.signals = WorkerSignals()

    def run(self):
        try:
            result = self.collector.run(self.query, self.pages, self.watch_rule_id,
                                        self.signals.progress.emit, self.profile_override)
            self.signals.finished.emit(result)
        except Exception as exc:
            logging.exception("Collection worker failed")
            self.signals.failed.emit(str(exc))


class WorkerEvents(QObject):
    """Receive worker signals on the GUI thread without exposing these slots to HTML."""

    def __init__(self, bridge):
        super().__init__(bridge)
        self.bridge = bridge

    @Slot(dict)
    def progress(self, item):
        self.bridge._emit("progress", item)

    @Slot(object)
    def finished(self, result):
        self.bridge._finished(result)

    @Slot(str)
    def failed(self, message):
        self.bridge._failed(message)


class Bridge(QObject):
    jobEvent = Signal(str)

    def __init__(self, store: Store, parent=None, notify=None):
        super().__init__(parent)
        self.store = store
        self.collector = Collector(store)
        self.notify = notify or (lambda _alert: None)
        self.pool = QThreadPool(self)
        self.pool.setMaxThreadCount(1)
        self.worker_events = WorkerEvents(self)
        self.running = False
        self.worker = None
        self.active_watches: set[int] = set()
        self.timer = QTimer(self)
        self.timer.setInterval(5000)
        self.timer.timeout.connect(self._tick)
        self.timer.start()

    def _emit(self, name: str, payload: dict):
        self.jobEvent.emit(json.dumps({"name": name, "payload": payload}, ensure_ascii=False))

    def _start(self, query: str, pages: int, rule_id: int | None = None,
               profile_override: SearchProfile | None = None):
        if self.running:
            raise ValueError("다른 수집 작업이 진행 중입니다.")
        self.worker = CollectWorker(self.collector, query, pages, rule_id, profile_override)
        self.worker.signals.progress.connect(self.worker_events.progress)
        self.worker.signals.finished.connect(self.worker_events.finished)
        self.worker.signals.failed.connect(self.worker_events.failed)
        self.running = True
        self._emit("started", {"query": query, "watch_rule_id": rule_id})
        self.pool.start(self.worker)

    def _finished(self, result):
        self.running = False
        self.worker = None
        summary = result.summary()
        self.notify(summary)
        self._emit("finished", {**result.__dict__, "summary": summary})
        QTimer.singleShot(0, self._tick)

    def _failed(self, message: str):
        worker = self.worker
        if worker and worker.watch_rule_id is not None:
            self.store.fail_watch(worker.watch_rule_id, message, worker.watch_generation,
                                  worker.watch_profile_version)
        self.running = False
        self.worker = None
        summary = {"title": "수집 실패", "message": message}
        self.notify(summary)
        self._emit("failed", {"message": message, "summary": summary})
        QTimer.singleShot(0, self._tick)

    def _tick(self):
        if self.running or not self.active_watches:
            return
        for rule in self.store.due_watches():
            if rule["id"] not in self.active_watches:
                continue
            try:
                self._start(rule["query"], self.store.get_profile().watch_pages, rule["id"])
            except Exception as exc:
                self.store.fail_watch(rule["id"], str(exc), rule["generation"],
                                      rule["profile_version"])
                summary = {"title": f"{rule['query']} · 감시 확인 실패", "message": str(exc)}
                self.notify(summary)
                self._emit("failed", {"message": str(exc), "summary": summary})
            break

    @Slot(str, str, result=str)
    def request(self, action: str, raw: str) -> str:
        try:
            data = json.loads(raw) if raw else {}
            answer = self._dispatch(action, data)
            return json.dumps({"ok": True, "data": answer}, ensure_ascii=False)
        except Exception as exc:
            logging.exception("UI request %s failed", action)
            return json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False)

    def _dispatch(self, action: str, data: dict):
        if action == "dashboard":
            return self.store.dashboard()
        if action == "postings":
            return self.store.list_postings(data.get("filters"), data.get("page", 1),
                                            sort=data.get("sort", "recent"))
        if action == "posting":
            return self.store.get_posting(str(data["id"]))
        if action == "facets":
            return self.store.facets()
        if action == "groups":
            return self.store.groups(data["kind"])
        if action == "analysis":
            return self.store.analyze(data.get("kind", "qualification"),
                                      data.get("filters"), data.get("page", 1))
        if action == "export_analysis":
            path, _ = QFileDialog.getSaveFileName(None, "분석 데이터 저장", "saramin-analysis.csv",
                                                  "CSV 파일 (*.csv)")
            return {"count": write_csv(export_rows(self.store, data["kind"], data.get("filters", {})),
                                       Path(path))} if path else {"cancelled": True}
        if action == "runs":
            return self.store.recent_runs()
        if action == "run_events":
            return self.store.run_events(int(data["id"]))
        if action == "profile":
            profile = self.store.get_profile()
            return {"name": profile.name, "version": profile.version, **profile.criteria()}
        if action == "profile_options":
            return [{"code": code, "label": label} for code, label in REGION_OPTIONS]
        if action == "save_profile":
            current = self.store.get_profile()
            updated = replace(
                current,
                location_codes=tuple(data["location_codes"]),
                experience_codes=tuple(data["experience_codes"]),
                experience_max=data["experience_max"],
                education_codes=tuple(data["education_codes"]),
            )
            saved = self.store.save_profile(updated)
            QTimer.singleShot(0, self._tick)
            return {"name": saved.name, "version": saved.version, **saved.criteria()}
        if action == "data_path":
            return str(self.store.path)
        if action == "settings":
            return {"font_percent": self.store.get_font_percent()}
        if action == "set_font_percent":
            return {"font_percent": self.store.set_font_percent(data["font_percent"])}
        if action == "open_url":
            target = urlparse(str(data["url"]))
            if target.scheme != "https" or target.netloc != "www.saramin.co.kr":
                raise ValueError("사람인 원본 공고 주소만 열 수 있습니다.")
            return {"opened": QDesktopServices.openUrl(QUrl(data["url"]))}
        if action == "watches":
            return [{**rule, "active": rule["id"] in self.active_watches}
                    for rule in self.store.list_watches()]
        if action == "alerts":
            return self.store.alerts()
        if action == "add_watch":
            return {"id": self.store.add_watch(data["query"], data["interval"])}
        if action == "update_watch":
            self.store.update_watch(data["id"], data["query"], data["interval"])
            QTimer.singleShot(0, self._tick)
            return {}
        if action == "start_watch":
            rule_id = int(data["id"])
            if not self.store.get_watch(rule_id):
                raise ValueError("감시 조건을 찾을 수 없습니다.")
            if rule_id not in self.active_watches:
                self.store.toggle_watch(rule_id, True)
                self.active_watches.add(rule_id)
            QTimer.singleShot(0, self._tick)
            return {"active": True}
        if action == "pause_watch":
            self.active_watches.discard(int(data["id"]))
            return {"active": False}
        if action == "delete_watch":
            self.active_watches.discard(int(data["id"]))
            self.store.delete_watch(data["id"])
            return {}
        if action == "read_alert":
            self.store.mark_alert_read(data["id"])
            return {}
        if action == "collect":
            criteria = data["criteria"]
            selected = validate_profile(replace(
                self.store.get_profile(),
                location_codes=tuple(criteria["location_codes"]),
                experience_codes=tuple(criteria["experience_codes"]),
                experience_max=criteria["experience_max"],
                education_codes=tuple(criteria["education_codes"]),
            ))
            self._start(data["query"], int(data["pages"]), profile_override=selected)
            return {"started": True}
        if action == "check_watch":
            rule = self.store.get_watch(data["id"])
            if not rule:
                raise ValueError("감시 조건을 선택해 주세요.")
            if not rule["enabled"]:
                self.store.toggle_watch(rule["id"], True)
            self._start(rule["query"], self.store.get_profile().watch_pages, rule["id"])
            return {"started": True}
        raise ValueError("지원하지 않는 화면 명령입니다.")
