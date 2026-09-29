"""Exercise the portable Qt watch scheduler without network or the user's DB."""

from __future__ import annotations

import json
import tempfile
import time
from pathlib import Path
from threading import Lock

from PySide6.QtCore import QCoreApplication

from saramin_finder.infrastructure.database import Store
from saramin_finder.ui.bridge import Bridge
from saramin_finder.usecases.collect import CollectResult


def main() -> int:
    app = QCoreApplication([])
    smoke_root = Path(__file__).resolve().parents[1] / ".smoke"
    smoke_root.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(dir=smoke_root) as temporary:
        store = Store(Path(temporary) / "watch.sqlite3")
        first = store.list_watches()[0]["id"]
        second = store.add_watch("백엔드", 1)
        calls: list[int] = []
        notices: list[dict] = []
        lock = Lock()
        active = {"count": 0, "maximum": 0}

        class FakeCollector:
            def __init__(self):
                self.store = store

            def run(self, query, pages, watch_rule_id, progress=None, profile_override=None):
                with lock:
                    active["count"] += 1
                    active["maximum"] = max(active["maximum"], active["count"])
                    calls.append(watch_rule_id)
                time.sleep(0.04)
                profile = store.get_profile()
                run_id = store.start_run("watch", query, profile, pages, watch_rule_id)
                store.finish_watch(watch_rule_id, [], expected_profile_version=profile.version)
                store.finish_run(run_id, "success", 0, 0, 0)
                with lock:
                    active["count"] -= 1
                return CollectResult(run_id, query=query, source="watch")

        def pump_until(count: int):
            deadline = time.monotonic() + 4
            while (len(notices) < count or len(calls) < count) and time.monotonic() < deadline:
                app.processEvents()
                time.sleep(0.01)
            app.processEvents()
            assert len(calls) == len(notices) == count, (calls, notices)

        bridge = Bridge(store, notify=notices.append)
        bridge.collector = FakeCollector()
        app.processEvents()
        assert not calls and not bridge.active_watches
        assert all(not rule["active"] for rule in bridge._dispatch("watches", {}))

        bridge._dispatch("start_watch", {"id": first})
        bridge._dispatch("start_watch", {"id": second})
        pump_until(2)
        assert calls == [first, second] and active["maximum"] == 1
        assert all(rule["active"] for rule in bridge._dispatch("watches", {}))

        with store.connect() as con:
            con.execute("UPDATE watch_rules SET next_due_at='2000-01-01T00:00:00+00:00' WHERE id=?",
                        (first,))
        bridge._tick()
        pump_until(3)
        assert calls[-1] == first

        bridge._dispatch("pause_watch", {"id": first})
        with store.connect() as con:
            con.execute("UPDATE watch_rules SET next_due_at='2000-01-01T00:00:00+00:00' WHERE id=?",
                        (first,))
        bridge._tick()
        for _ in range(20):
            app.processEvents()
            time.sleep(0.01)
        assert len(calls) == 3 and not bridge._dispatch("watches", {})[0]["active"]

        bridge.timer.stop()
        reopened = Bridge(store, notify=notices.append)
        reopened.collector = FakeCollector()
        reopened._tick()
        app.processEvents()
        assert not reopened.active_watches and len(calls) == 3

        reopened._dispatch("check_watch", {"id": first})
        pump_until(4)
        assert calls[-1] == first and not reopened.active_watches
        reopened.timer.stop()
        print(json.dumps({"runs": len(calls), "max_concurrent": active["maximum"],
                          "notifications": len(notices), "restart_active": False}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
