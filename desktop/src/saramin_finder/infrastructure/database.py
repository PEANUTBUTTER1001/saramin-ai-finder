from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterable
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

from saramin_finder.domain.models import PROVIDERS, Detail, Posting, SearchProfile
from saramin_finder.domain.rules import (keywords_in, normalize_query, sector_keywords, validate_interval,
                                         validate_profile, validate_query)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def after_minutes(minutes: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(minutes=minutes)).isoformat(timespec="seconds")


def watch_query_key(query: str, provider: str) -> str:
    if provider not in PROVIDERS:
        raise ValueError("수집 출처를 선택해 주세요.")
    normalized = normalize_query(query)
    # Normalized legacy queries never contain newlines, so existing keys stay valid.
    return normalized if provider == "saramin" else f"{provider}\n{normalized}"


class Store:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    @contextmanager
    def connect(self):
        con = sqlite3.connect(self.path, timeout=20)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA foreign_keys=ON")
        try:
            yield con
            con.commit()
        except Exception:
            con.rollback()
            raise
        finally:
            con.close()

    def _initialize(self):
        with self.connect() as con:
            con.execute("PRAGMA journal_mode=WAL")
            version = con.execute("PRAGMA user_version").fetchone()[0]
            if version > 8:
                raise RuntimeError("이 앱보다 새로운 데이터베이스입니다. 기존 파일을 변경하지 않았습니다.")
            if version == 0:
                con.executescript("""BEGIN IMMEDIATE;
                CREATE TABLE search_profiles (
                  id INTEGER PRIMARY KEY, name TEXT NOT NULL, version INTEGER NOT NULL,
                  criteria_json TEXT NOT NULL
                );
                CREATE TABLE postings (
                  rec_idx TEXT PRIMARY KEY, company TEXT NOT NULL, title TEXT NOT NULL,
                  url TEXT NOT NULL, sector TEXT NOT NULL DEFAULT '',
                  career TEXT NOT NULL DEFAULT '', education TEXT NOT NULL DEFAULT '',
                  conditions TEXT NOT NULL DEFAULT '', deadline TEXT NOT NULL DEFAULT '',
                  posted_date TEXT NOT NULL DEFAULT '', updated_date TEXT NOT NULL DEFAULT '',
                  deadline_date TEXT NOT NULL DEFAULT '',
                  full_text TEXT NOT NULL DEFAULT '', detail_status TEXT NOT NULL DEFAULT 'pending',
                  first_seen_at TEXT NOT NULL, last_seen_at TEXT NOT NULL
                );
                CREATE TABLE posting_sections (
                  posting_id TEXT NOT NULL REFERENCES postings(rec_idx) ON DELETE CASCADE,
                  kind TEXT NOT NULL CHECK(kind IN ('main_work','qualification','preference')),
                  text TEXT NOT NULL DEFAULT '', status TEXT NOT NULL,
                  parser_version INTEGER NOT NULL, updated_at TEXT NOT NULL,
                  PRIMARY KEY(posting_id,kind)
                );
                CREATE TABLE section_keywords (
                  posting_id TEXT NOT NULL, kind TEXT NOT NULL, keyword TEXT NOT NULL,
                  PRIMARY KEY(posting_id,kind,keyword),
                  FOREIGN KEY(posting_id,kind) REFERENCES posting_sections(posting_id,kind) ON DELETE CASCADE
                );
                CREATE TABLE crawl_runs (
                  id INTEGER PRIMARY KEY AUTOINCREMENT, source TEXT NOT NULL,
                  watch_rule_id INTEGER, query TEXT NOT NULL, profile_snapshot TEXT NOT NULL,
                  page_limit INTEGER NOT NULL, started_at TEXT NOT NULL, finished_at TEXT,
                  status TEXT NOT NULL DEFAULT 'running', new_count INTEGER NOT NULL DEFAULT 0,
                  updated_count INTEGER NOT NULL DEFAULT 0, failed_count INTEGER NOT NULL DEFAULT 0,
                  error TEXT NOT NULL DEFAULT ''
                );
                CREATE TABLE crawl_run_postings (
                  run_id INTEGER NOT NULL REFERENCES crawl_runs(id) ON DELETE CASCADE,
                  posting_id TEXT NOT NULL REFERENCES postings(rec_idx),
                  PRIMARY KEY(run_id,posting_id)
                );
                CREATE TABLE watch_rules (
                  id INTEGER PRIMARY KEY AUTOINCREMENT, query TEXT NOT NULL,
                  normalized_query TEXT NOT NULL UNIQUE, interval_minutes INTEGER NOT NULL,
                  enabled INTEGER NOT NULL DEFAULT 1, baseline_ready INTEGER NOT NULL DEFAULT 0,
                  generation INTEGER NOT NULL DEFAULT 0, profile_version INTEGER NOT NULL,
                  last_success_at TEXT, next_due_at TEXT, last_result TEXT NOT NULL DEFAULT '첫 확인 대기'
                );
                CREATE TABLE watch_seen (
                  rule_id INTEGER NOT NULL REFERENCES watch_rules(id) ON DELETE CASCADE,
                  posting_id TEXT NOT NULL REFERENCES postings(rec_idx),
                  PRIMARY KEY(rule_id,posting_id)
                );
                CREATE TABLE alerts (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  rule_id INTEGER REFERENCES watch_rules(id) ON DELETE SET NULL,
                  generation INTEGER NOT NULL, query_snapshot TEXT NOT NULL,
                  posting_id TEXT NOT NULL REFERENCES postings(rec_idx),
                  created_at TEXT NOT NULL, read_at TEXT,
                  UNIQUE(rule_id,generation,posting_id)
                );
                CREATE INDEX postings_last_seen_idx ON postings(last_seen_at DESC);
                CREATE INDEX postings_company_idx ON postings(company);
                CREATE INDEX postings_sector_idx ON postings(sector);
                CREATE INDEX watch_due_idx ON watch_rules(enabled,next_due_at);
                CREATE INDEX alerts_created_idx ON alerts(created_at DESC);
                CREATE TABLE schema_version (version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL);
                """)
                profile = SearchProfile()
                con.execute(
                    "INSERT INTO search_profiles VALUES (?,?,?,?)",
                    (profile.id, profile.name, profile.version, json.dumps(profile.criteria(), ensure_ascii=False)),
                )
                con.execute("INSERT INTO schema_version VALUES (?,?)", (1, utc_now()))
                con.execute("PRAGMA user_version=1")
            if version <= 1:
                # Install the requested AI watch once. A user who later deletes it keeps that choice.
                if not con.execute("SELECT 1 FROM watch_rules WHERE normalized_query=?",
                                   (normalize_query("AI"),)).fetchone():
                    con.execute("""INSERT INTO watch_rules(query,normalized_query,interval_minutes,
                        profile_version,next_due_at) VALUES (?,?,?,?,?)""",
                        ("AI", normalize_query("AI"), 60, 1, utc_now()))
                con.execute("INSERT OR IGNORE INTO schema_version VALUES (?,?)", (2, utc_now()))
                con.execute("PRAGMA user_version=2")
            if version <= 2:
                # The old web-search edu_cd=4 did not mean 4-year college or above.
                row = con.execute("SELECT version,criteria_json FROM search_profiles WHERE id=1").fetchone()
                criteria = json.loads(row["criteria_json"])
                if "4" in criteria["education_codes"]:
                    criteria["education_codes"] = list(dict.fromkeys(
                        "8" if code == "4" else code for code in criteria["education_codes"]))
                    next_version = row["version"] + 1
                    con.execute("UPDATE search_profiles SET version=?,criteria_json=? WHERE id=1",
                                (next_version, json.dumps(criteria, ensure_ascii=False)))
                    con.execute("DELETE FROM watch_seen")
                    con.execute("""UPDATE watch_rules SET baseline_ready=0,
                        generation=generation+1,profile_version=?,
                        last_result='학력 조건 수정 · 기준 재설정',
                        next_due_at=CASE WHEN enabled=1 THEN ? ELSE NULL END""",
                        (next_version, utc_now()))
                con.execute("INSERT OR IGNORE INTO schema_version VALUES (?,?)", (3, utc_now()))
                con.execute("PRAGMA user_version=3")
            if version <= 3:
                if version != 0:
                    existing = {row[1] for row in con.execute("PRAGMA table_info(postings)")}
                    for column in ("posted_date", "updated_date", "deadline_date"):
                        if column not in existing:
                            con.execute(f"ALTER TABLE postings ADD COLUMN {column} TEXT NOT NULL DEFAULT ''")
                con.execute("CREATE INDEX IF NOT EXISTS postings_posted_date_idx ON postings(posted_date)")
                con.execute("CREATE INDEX IF NOT EXISTS postings_deadline_date_idx ON postings(deadline_date)")
                con.execute("INSERT OR IGNORE INTO schema_version VALUES (?,?)", (4, utc_now()))
                con.execute("PRAGMA user_version=4")
            if version <= 4:
                tables = {row[0] for row in con.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'")}
                if {"crawl_runs", "crawl_run_postings"}.issubset(tables):
                    run_columns = {row[1] for row in con.execute("PRAGMA table_info(crawl_runs)")}
                    for column, definition in (("comparison_ready", "INTEGER NOT NULL DEFAULT 0"),
                                               *((name, "INTEGER") for name in
                                                 ("baseline_run_id", "discovered_count", "registered_count",
                                                  "changed_count", "missing_count", "closed_count"))):
                        if column not in run_columns:
                            con.execute(f"ALTER TABLE crawl_runs ADD COLUMN {column} {definition}")
                    posting_columns = {row[1] for row in con.execute(
                        "PRAGMA table_info(crawl_run_postings)")}
                    if "snapshot_json" not in posting_columns:
                        con.execute("ALTER TABLE crawl_run_postings ADD COLUMN snapshot_json TEXT NOT NULL DEFAULT ''")
                    if "detail_ok" not in posting_columns:
                        con.execute("ALTER TABLE crawl_run_postings ADD COLUMN detail_ok INTEGER NOT NULL DEFAULT 0")
                    con.execute("""CREATE TABLE IF NOT EXISTS crawl_run_events (
                        run_id INTEGER NOT NULL REFERENCES crawl_runs(id) ON DELETE CASCADE,
                        posting_id TEXT NOT NULL REFERENCES postings(rec_idx),
                        kind TEXT NOT NULL CHECK(kind IN ('discovered','registered','changed','missing','closed')),
                        PRIMARY KEY(run_id,posting_id,kind))""")
                con.execute("INSERT OR IGNORE INTO schema_version VALUES (?,?)", (5, utc_now()))
                con.execute("PRAGMA user_version=5")
            if version <= 5:
                con.execute("""CREATE TABLE IF NOT EXISTS posting_sector_keywords (
                    posting_id TEXT NOT NULL REFERENCES postings(rec_idx) ON DELETE CASCADE,
                    keyword TEXT NOT NULL, PRIMARY KEY(posting_id,keyword))""")
                con.execute("CREATE INDEX IF NOT EXISTS sector_keyword_idx ON posting_sector_keywords(keyword)")
                con.execute("""CREATE TABLE IF NOT EXISTS app_settings (
                    key TEXT PRIMARY KEY, value TEXT NOT NULL)""")
                con.execute("INSERT OR IGNORE INTO app_settings(key,value) VALUES ('font_percent','100')")
                for row in con.execute("SELECT rec_idx,sector FROM postings"):
                    con.executemany("INSERT OR IGNORE INTO posting_sector_keywords VALUES (?,?)",
                                    ((row["rec_idx"], word) for word in sector_keywords(row["sector"])))
                con.execute("INSERT OR IGNORE INTO schema_version VALUES (?,?)", (6, utc_now()))
                con.execute("PRAGMA user_version=6")
            if version <= 6:
                columns = {row[1] for row in con.execute("PRAGMA table_info(postings)")}
                for name, definition in (
                    ("favorite", "INTEGER NOT NULL DEFAULT 0 CHECK(favorite IN (0,1))"),
                    ("first_watch_collected_at", "TEXT NOT NULL DEFAULT ''"),
                    ("last_watch_collected_at", "TEXT NOT NULL DEFAULT ''"),
                ):
                    if name not in columns:
                        con.execute(f"ALTER TABLE postings ADD COLUMN {name} {definition}")
                alert_columns = {row[1] for row in con.execute("PRAGMA table_info(alerts)")}
                if alert_columns and "collected_at" not in alert_columns:
                    con.execute("ALTER TABLE alerts ADD COLUMN collected_at TEXT NOT NULL DEFAULT ''")
                con.execute("INSERT OR IGNORE INTO app_settings VALUES ('sidebar_collapsed','0')")
                con.execute("INSERT OR IGNORE INTO schema_version VALUES (?,?)", (7, utc_now()))
                con.execute("PRAGMA user_version=7")
            if version <= 7:
                if not con.in_transaction:
                    con.execute("BEGIN IMMEDIATE")
                for table in ("postings", "crawl_runs", "watch_rules"):
                    columns = {row[1] for row in con.execute(f"PRAGMA table_info({table})")}
                    if columns and "provider" not in columns:
                        con.execute(f"ALTER TABLE {table} ADD COLUMN provider TEXT NOT NULL DEFAULT 'saramin'")
                con.execute("INSERT OR IGNORE INTO schema_version VALUES (?,?)", (8, utc_now()))
                con.execute("PRAGMA user_version=8")

    def get_theme(self) -> str:
        with self.connect() as con:
            row = con.execute("SELECT value FROM app_settings WHERE key='theme'").fetchone()
        return row[0] if row and row[0] in ("light", "dark") else "light"

    def set_theme(self, theme: str) -> str:
        if not isinstance(theme, str) or theme not in ("light", "dark"):
            raise ValueError("화면 모드는 라이트 또는 다크로 선택해 주세요.")
        with self.connect() as con:
            con.execute("""INSERT INTO app_settings(key,value) VALUES ('theme',?)
                ON CONFLICT(key) DO UPDATE SET value=excluded.value""", (theme,))
        return theme

    def get_sidebar_collapsed(self) -> bool:
        with self.connect() as con:
            return con.execute("SELECT value FROM app_settings WHERE key='sidebar_collapsed'").fetchone()[0] == "1"

    def set_sidebar_collapsed(self, collapsed: bool) -> bool:
        if not isinstance(collapsed, bool):
            raise ValueError("사이드바 축소 상태가 올바르지 않습니다.")
        with self.connect() as con:
            con.execute("UPDATE app_settings SET value=? WHERE key='sidebar_collapsed'", (str(int(collapsed)),))
        return collapsed

    def set_favorite(self, rec_idx: str, favorite: bool) -> dict:
        if not isinstance(favorite, bool):
            raise ValueError("즐겨찾기 상태가 올바르지 않습니다.")
        with self.connect() as con:
            changed = con.execute("UPDATE postings SET favorite=? WHERE rec_idx=?", (int(favorite), rec_idx))
            if not changed.rowcount:
                raise ValueError("저장된 공고를 찾을 수 없습니다.")
        return {"id": rec_idx, "favorite": favorite}

    def get_font_percent(self) -> int:
        with self.connect() as con:
            return int(con.execute("SELECT value FROM app_settings WHERE key='font_percent'").fetchone()[0])

    def set_font_percent(self, percent: int) -> int:
        if isinstance(percent, bool) or not isinstance(percent, int) or percent not in range(80, 141, 10):
            raise ValueError("글자 크기는 80~140%에서 10% 단위로 선택해 주세요.")
        with self.connect() as con:
            con.execute("UPDATE app_settings SET value=? WHERE key='font_percent'", (str(percent),))
        return percent

    def get_profile(self) -> SearchProfile:
        with self.connect() as con:
            row = con.execute("SELECT * FROM search_profiles WHERE id=1").fetchone()
        data = json.loads(row["criteria_json"])
        return SearchProfile(
            id=row["id"], name=row["name"], version=row["version"],
            location_codes=tuple(data["location_codes"]),
            experience_codes=tuple(data["experience_codes"]),
            experience_max=data["experience_max"],
            education_codes=tuple(data["education_codes"]),
            sort=data["sort"], watch_pages=data["watch_pages"],
        )

    def save_profile(self, profile: SearchProfile) -> SearchProfile:
        validate_profile(profile)
        current = self.get_profile()
        if profile.criteria() == current.criteria() and profile.name == current.name:
            return current
        with self.connect() as con:
            old = con.execute("SELECT version FROM search_profiles WHERE id=1").fetchone()
            version = old[0] + 1
            con.execute(
                "UPDATE search_profiles SET name=?, version=?, criteria_json=? WHERE id=1",
                (profile.name, version, json.dumps(profile.criteria(), ensure_ascii=False)),
            )
            con.execute("DELETE FROM watch_seen")
            con.execute("""UPDATE watch_rules SET baseline_ready=0, generation=generation+1,
                        profile_version=?, last_result='검색 조건 변경 · 기준 재설정',
                        next_due_at=CASE WHEN enabled=1 THEN ? ELSE NULL END""", (version, utc_now()))
        return self.get_profile()

    def start_run(self, source: str, query: str, profile: SearchProfile, page_limit: int,
                  watch_rule_id: int | None = None, provider: str = "saramin") -> int:
        with self.connect() as con:
            cur = con.execute(
                """INSERT INTO crawl_runs(source,watch_rule_id,query,profile_snapshot,page_limit,started_at,provider)
                   VALUES (?,?,?,?,?,?,?)""",
                (source, watch_rule_id, query, json.dumps(profile.criteria(), ensure_ascii=False),
                  page_limit, utc_now(), provider),
            )
            return cur.lastrowid

    def finish_run(self, run_id: int, status: str, new_count: int, updated_count: int,
                   failed_count: int, error: str = "", metrics: dict | None = None, *,
                   listing_complete: bool | None = None):
        metrics = metrics or {}
        comparison_ready = status == "success" if listing_complete is None else listing_complete
        with self.connect() as con:
            con.execute("""UPDATE crawl_runs SET status=?, finished_at=?, new_count=?,
                       updated_count=?, failed_count=?, error=?, comparison_ready=?,
                       baseline_run_id=?, discovered_count=?, registered_count=?,
                       changed_count=?, missing_count=?, closed_count=? WHERE id=?""",
                        (status, utc_now(), new_count, updated_count, failed_count, error[:2000],
                          int(comparison_ready), metrics.get("baseline_run_id"),
                         metrics.get("discovered_count"), metrics.get("registered_count"),
                         metrics.get("changed_count"), metrics.get("missing_count"),
                         metrics.get("closed_count"), run_id))

    def comparable_run(self, query: str, profile: SearchProfile, pages: int,
                       provider: str = "saramin") -> dict | None:
        snapshot = json.dumps(profile.criteria(), ensure_ascii=False)
        with self.connect() as con:
            rows = con.execute("""SELECT id,query,finished_at FROM crawl_runs
                WHERE status IN ('success', 'partial') AND comparison_ready=1 AND profile_snapshot=?
                   AND page_limit=? AND provider=? ORDER BY id DESC""", (snapshot, pages, provider))
            return next((dict(row) for row in rows
                         if normalize_query(row["query"]) == normalize_query(query)), None)

    def run_snapshots(self, run_id: int) -> dict[str, dict]:
        with self.connect() as con:
            return {row["posting_id"]: {"values": json.loads(row["snapshot_json"]),
                                        "detail_ok": bool(row["detail_ok"]), "url": row["url"]}
                    for row in con.execute("""SELECT crp.posting_id,crp.snapshot_json,crp.detail_ok,p.url
                        FROM crawl_run_postings crp JOIN postings p ON p.rec_idx=crp.posting_id
                        WHERE crp.run_id=? AND crp.snapshot_json<>''""", (run_id,))}

    def record_snapshot(self, run_id: int, posting_id: str, values: dict, detail_ok: bool):
        with self.connect() as con:
            con.execute("""UPDATE crawl_run_postings SET snapshot_json=?,detail_ok=?
                WHERE run_id=? AND posting_id=?""",
                (json.dumps(values, ensure_ascii=False, sort_keys=True), int(detail_ok),
                 run_id, posting_id))

    def record_events(self, run_id: int, events: dict[str, set[str]]):
        with self.connect() as con:
            con.executemany("INSERT OR IGNORE INTO crawl_run_events VALUES (?,?,?)",
                            [(run_id, posting_id, kind) for kind, ids in events.items()
                             for posting_id in ids])

    def run_events(self, run_id: int) -> list[dict]:
        with self.connect() as con:
            return [dict(row) for row in con.execute("""SELECT e.kind,e.posting_id,
                p.company,p.title,p.url FROM crawl_run_events e
                JOIN postings p ON p.rec_idx=e.posting_id WHERE e.run_id=?
                ORDER BY e.kind,p.company,p.title""", (run_id,))]

    def save_posting(self, posting: Posting, detail: Detail, run_id: int) -> bool:
        stamp = utc_now()
        with self.connect() as con:
            existed = con.execute("SELECT detail_status FROM postings WHERE rec_idx=?", (posting.rec_idx,)).fetchone()
            con.execute("""INSERT INTO postings
                (rec_idx,company,title,url,sector,career,education,conditions,deadline,
                 posted_date,updated_date,deadline_date,full_text,detail_status,first_seen_at,last_seen_at,provider)
                 VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(rec_idx) DO UPDATE SET
                  company=excluded.company,title=excluded.title,url=excluded.url,
                  sector=excluded.sector,career=excluded.career,education=excluded.education,
                  conditions=excluded.conditions,deadline=excluded.deadline,
                  posted_date=CASE WHEN excluded.posted_date<>'' THEN excluded.posted_date
                                   ELSE postings.posted_date END,
                  updated_date=CASE WHEN excluded.updated_date<>'' THEN excluded.updated_date
                                    ELSE postings.updated_date END,
                  deadline_date=excluded.deadline_date,
                  last_seen_at=excluded.last_seen_at""",
                (posting.rec_idx, posting.company, posting.title, posting.url, posting.sector,
                 posting.career, posting.education, posting.conditions, posting.deadline,
                 posting.posted_date, posting.updated_date, posting.deadline_date,
                 "", "pending", stamp, stamp, posting.provider))
            run = con.execute("SELECT source FROM crawl_runs WHERE id=?", (run_id,)).fetchone()
            if run and run["source"] == "watch":
                con.execute("""UPDATE postings SET
                    first_watch_collected_at=CASE WHEN first_watch_collected_at='' THEN ?
                                                 ELSE first_watch_collected_at END,
                    last_watch_collected_at=? WHERE rec_idx=?""", (stamp, stamp, posting.rec_idx))
            con.execute("DELETE FROM posting_sector_keywords WHERE posting_id=?", (posting.rec_idx,))
            con.executemany("INSERT INTO posting_sector_keywords VALUES (?,?)",
                            ((posting.rec_idx, word) for word in sector_keywords(posting.sector)))
            if detail.status == "complete" or (detail.status == "image_only" and
                                               (not existed or existed["detail_status"] != "complete")):
                con.execute("UPDATE postings SET full_text=?, detail_status=? WHERE rec_idx=?",
                            (detail.full_text, detail.status, posting.rec_idx))
                for kind in ("main_work", "qualification", "preference"):
                    section_text = detail.sections.get(kind, "")
                    con.execute("""INSERT INTO posting_sections VALUES (?,?,?,?,?,?)
                        ON CONFLICT(posting_id,kind) DO UPDATE SET text=excluded.text,
                        status=excluded.status,parser_version=excluded.parser_version,
                        updated_at=excluded.updated_at""",
                        (posting.rec_idx, kind, section_text,
                         detail.section_status.get(kind, "missing"), detail.parser_version, stamp))
                    con.execute("DELETE FROM section_keywords WHERE posting_id=? AND kind=?",
                                (posting.rec_idx, kind))
                    if detail.section_status.get(kind) == "extracted":
                        con.executemany(
                            "INSERT INTO section_keywords VALUES (?,?,?)",
                            [(posting.rec_idx, kind, word) for word in keywords_in(section_text)],
                        )
            elif not existed or existed["detail_status"] != "complete":
                con.execute("UPDATE postings SET detail_status='failed' WHERE rec_idx=?",
                            (posting.rec_idx,))
            con.execute("""INSERT OR IGNORE INTO crawl_run_postings(run_id,posting_id)
                VALUES (?,?)""", (run_id, posting.rec_idx))
            return existed is None

    def _where(self, filters: dict, section_kind: str | None = None):
        clauses, args = [], []
        if filters.get("favorite"):
            clauses.append("p.favorite=1")
        def choices(key):
            raw = filters.get(key) or []
            if isinstance(raw, str):
                raw = [raw]
            return list(dict.fromkeys(str(item) for item in raw if str(item).strip()))[:200]

        for key in ("company", "career", "provider"):
            values = choices(key)
            if values:
                clauses.append(f"p.{key} IN ({','.join('?' for _ in values)})")
                args.extend(values)
        sectors = choices("sector")
        if sectors:
            clauses.append("EXISTS (SELECT 1 FROM posting_sector_keywords psk WHERE "
                           "psk.posting_id=p.rec_idx AND psk.keyword IN (" +
                           ",".join("?" for _ in sectors) + "))")
            args.extend(sectors)
        for key, column in (("group_sector", "sector"), ("group_career", "career"),
                            ("group_tech", "tech"), ("group_company", "company")):
            value = filters.get(key)
            if not value:
                continue
            if column == "sector":
                clauses.append("EXISTS (SELECT 1 FROM posting_sector_keywords psk WHERE "
                               "psk.posting_id=p.rec_idx AND psk.keyword=?)")
            elif column == "tech":
                clauses.append("EXISTS (SELECT 1 FROM section_keywords sk WHERE "
                               "sk.posting_id=p.rec_idx AND sk.keyword=?)")
            else:
                clauses.append(f"p.{column}=?")
            args.append(value)
        techs = choices("tech")
        if techs:
            placeholders = ",".join("?" for _ in techs)
            if section_kind:
                clauses.append("EXISTS (SELECT 1 FROM section_keywords sk WHERE "
                               f"sk.posting_id=p.rec_idx AND sk.kind=? AND sk.keyword IN ({placeholders}))")
                args.append(section_kind)
            else:
                clauses.append("EXISTS (SELECT 1 FROM section_keywords sk WHERE "
                               f"sk.posting_id=p.rec_idx AND sk.keyword IN ({placeholders}))")
            args.extend(techs)
        if filters.get("query"):
            clauses.append("""EXISTS (SELECT 1 FROM crawl_run_postings crp JOIN crawl_runs cr
                            ON cr.id=crp.run_id WHERE crp.posting_id=p.rec_idx AND cr.query=?)""")
            args.append(filters["query"])
        if filters.get("date"):
            clauses.append("substr(p.last_seen_at,1,10)=?")
            args.append(filters["date"])
        if filters.get("text"):
            value = str(filters["text"]).replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            cols = "p.company || ' ' || p.title || ' ' || p.full_text"
            if section_kind:
                cols = "s.text"
            clauses.append(f"{cols} LIKE ? ESCAPE '\\'")
            args.append(f"%{value}%")
        return (" WHERE " + " AND ".join(clauses)) if clauses else "", args

    def list_postings(self, filters: dict | None = None, page: int = 1, per_page: int = 40,
                      sort: str = "recent") -> dict:
        filters = filters or {}
        per_page = max(1, min(100, int(per_page)))
        where, args = self._where(filters)
        today = datetime.now(timezone(timedelta(hours=9))).date().isoformat()
        order = {
            "recent": "p.last_seen_at DESC",
            "company": "p.company COLLATE NOCASE ASC",
            "posted_newest": "(p.posted_date='') ASC, p.posted_date DESC",
            "posted_oldest": "(p.posted_date='') ASC, p.posted_date ASC",
            "deadline_soon": "CASE WHEN p.deadline_date='' THEN 2 WHEN p.deadline_date < '{today}' THEN 1 ELSE 0 END, p.deadline_date ASC",
            "deadline_late": "CASE WHEN p.deadline_date='' THEN 2 WHEN p.deadline_date < '{today}' THEN 1 ELSE 0 END, p.deadline_date DESC",
        }.get(sort, "p.last_seen_at DESC").format(today=today)
        page = max(1, int(page))
        with self.connect() as con:
            total = con.execute("SELECT COUNT(*) FROM postings p" + where, args).fetchone()[0]
            rows = con.execute(
                "SELECT p.* FROM postings p" + where + f" ORDER BY {order}, p.rec_idx DESC LIMIT ? OFFSET ?",
                [*args, per_page, (page - 1) * per_page],
            ).fetchall()
            items = [dict(row) for row in rows]
            for item in items:
                item["tech"] = [x[0] for x in con.execute(
                    "SELECT DISTINCT keyword FROM section_keywords WHERE posting_id=? ORDER BY keyword",
                    (item["rec_idx"],))]
                item.pop("full_text")
        return {"items": items, "total": total, "page": page, "per_page": per_page}

    def get_posting(self, rec_idx: str) -> dict | None:
        with self.connect() as con:
            row = con.execute("SELECT * FROM postings WHERE rec_idx=?", (rec_idx,)).fetchone()
            if not row:
                return None
            item = dict(row)
            item["sections"] = {x["kind"]: {"text": x["text"], "status": x["status"]}
                                for x in con.execute("SELECT * FROM posting_sections WHERE posting_id=?", (rec_idx,))}
            item["keywords"] = {kind: [x[0] for x in con.execute(
                "SELECT keyword FROM section_keywords WHERE posting_id=? AND kind=? ORDER BY keyword",
                (rec_idx, kind))] for kind in ("qualification", "preference")}
            item["queries"] = [x[0] for x in con.execute("""SELECT DISTINCT cr.query FROM crawl_runs cr
                JOIN crawl_run_postings crp ON crp.run_id=cr.id WHERE crp.posting_id=? ORDER BY cr.id DESC""",
                (rec_idx,))]
            return item

    def dashboard(self) -> dict:
        with self.connect() as con:
            p = con.execute("""SELECT COUNT(*) total, COUNT(DISTINCT company) companies,
                   SUM(CASE WHEN detail_status='complete' THEN 1 ELSE 0 END) details FROM postings""").fetchone()
            tech = con.execute("SELECT COUNT(DISTINCT keyword) FROM section_keywords").fetchone()[0]
            sectors = [dict(x) for x in con.execute("""SELECT keyword value,COUNT(*) count
                FROM posting_sector_keywords GROUP BY keyword ORDER BY count DESC LIMIT 10""")]
            run = con.execute("SELECT * FROM crawl_runs ORDER BY id DESC LIMIT 1").fetchone()
            return {"total": p["total"], "companies": p["companies"], "details": p["details"] or 0,
                    "tech": tech, "sectors": sectors, "last_run": dict(run) if run else None}

    def facets(self) -> dict:
        with self.connect() as con:
            result = {}
            for col in ("company", "career"):
                result[col] = [x[0] for x in con.execute(
                    f"SELECT DISTINCT {col} FROM postings WHERE {col}<>'' ORDER BY {col}")]
            result["sector"] = [x[0] for x in con.execute(
                "SELECT DISTINCT keyword FROM posting_sector_keywords ORDER BY keyword")]
            result["tech"] = [x[0] for x in con.execute(
                "SELECT DISTINCT keyword FROM section_keywords ORDER BY keyword")]
            result["query"] = [x[0] for x in con.execute(
                "SELECT DISTINCT query FROM crawl_runs ORDER BY query")]
            return result

    def groups(self, kind: str, provider: str = "") -> list[dict]:
        with self.connect() as con:
            if kind == "tech":
                sql = """SELECT keyword value,COUNT(DISTINCT posting_id) count FROM section_keywords
                         JOIN postings p ON p.rec_idx=posting_id"""
            elif kind == "sector":
                sql = """SELECT keyword value,COUNT(*) count FROM posting_sector_keywords
                         JOIN postings p ON p.rec_idx=posting_id"""
            elif kind == "date":
                sql = "SELECT substr(p.last_seen_at,1,10) value,COUNT(*) count FROM postings p"
            elif kind in ("company", "career"):
                sql = f"SELECT p.{kind} value,COUNT(*) count FROM postings p"
            else:
                raise ValueError("지원하지 않는 분류입니다.")
            where, args = self._where({"provider": provider})
            return [dict(x) for x in con.execute(
                sql + where + " GROUP BY value ORDER BY count DESC,value ASC LIMIT 100", args)]

    def analyze(self, kind: str, filters: dict | None = None, page: int = 1,
                per_page: int = 40) -> dict:
        if kind not in ("qualification", "preference"):
            raise ValueError("자격요건 또는 우대사항을 선택해 주세요.")
        filters = filters or {}
        where, args = self._where(filters, kind)
        where += (" AND " if where else " WHERE ") + "s.kind=? AND s.status='extracted'"
        args.append(kind)
        with self.connect() as con:
            total = con.execute("SELECT COUNT(*) FROM postings p JOIN posting_sections s ON s.posting_id=p.rec_idx" + where, args).fetchone()[0]
            rows = [dict(x) for x in con.execute("""SELECT p.rec_idx,p.company,p.title,p.sector,p.career,
                p.provider,p.url,p.last_seen_at,s.text FROM postings p JOIN posting_sections s ON s.posting_id=p.rec_idx"""
                + where + " ORDER BY p.last_seen_at DESC,p.rec_idx DESC LIMIT ? OFFSET ?",
                [*args, per_page, (max(1, page) - 1) * per_page])]
            keywords = [dict(x) for x in con.execute("""SELECT sk.keyword,COUNT(DISTINCT sk.posting_id) count
                FROM section_keywords sk JOIN postings p ON p.rec_idx=sk.posting_id
                JOIN posting_sections s ON s.posting_id=p.rec_idx AND s.kind=sk.kind"""
                + where + " GROUP BY sk.keyword ORDER BY count DESC,sk.keyword LIMIT 30", args)]
        return {"items": rows, "total": total, "page": page, "keywords": keywords}

    def recent_runs(self, limit: int = 20) -> list[dict]:
        with self.connect() as con:
            return [dict(x) for x in con.execute("SELECT * FROM crawl_runs ORDER BY id DESC LIMIT ?", (limit,))]

    def add_watch(self, query: str, interval_minutes: int, provider: str = "saramin") -> int:
        added = self.add_watches(query, interval_minutes, (provider,))
        if not added:
            raise ValueError("이미 감시 중인 검색어입니다. 목록에서 기존 조건을 수정해 주세요.")
        return added[0]

    def add_watches(self, query: str, interval_minutes: int, providers: tuple[str, ...]) -> list[int]:
        query = validate_query(query, 30 if "jobkorea" in providers else 40)
        interval_minutes = validate_interval(interval_minutes)
        keys = [(provider, watch_query_key(query, provider)) for provider in providers]
        added = []
        with self.connect() as con:
            stamp = utc_now()
            for provider, key in keys:
                cur = con.execute("""INSERT INTO watch_rules(query,normalized_query,interval_minutes,
                    profile_version,next_due_at,provider)
                    SELECT ?,?,?,version,?,? FROM search_profiles WHERE id=1
                    ON CONFLICT(normalized_query) DO NOTHING""",
                    (query, key, interval_minutes, stamp, provider))
                if cur.rowcount:
                    added.append(cur.lastrowid)
        return added

    def list_watches(self) -> list[dict]:
        with self.connect() as con:
            return [dict(x) for x in con.execute("SELECT * FROM watch_rules ORDER BY id")]

    def get_watch(self, rule_id: int) -> dict | None:
        with self.connect() as con:
            row = con.execute("SELECT * FROM watch_rules WHERE id=?", (rule_id,)).fetchone()
            return dict(row) if row else None

    def update_watch(self, rule_id: int, query: str, interval_minutes: int):
        interval_minutes = validate_interval(interval_minutes)
        with self.connect() as con:
            old = con.execute("SELECT * FROM watch_rules WHERE id=?", (rule_id,)).fetchone()
            if not old:
                raise ValueError("감시 조건을 찾을 수 없습니다.")
            query = validate_query(query, 30 if old["provider"] == "jobkorea" else 40)
            key = watch_query_key(query, old["provider"])
            if con.execute("SELECT 1 FROM watch_rules WHERE normalized_query=? AND id<>?",
                           (key, rule_id)).fetchone():
                raise ValueError("이미 감시 중인 검색어입니다.")
            changed = key != old["normalized_query"]
            if changed:
                con.execute("DELETE FROM watch_seen WHERE rule_id=?", (rule_id,))
            con.execute("""UPDATE watch_rules SET query=?,normalized_query=?,interval_minutes=?,
                baseline_ready=?,generation=?,last_result=?,next_due_at=? WHERE id=?""",
                (query, key, interval_minutes,
                 0 if changed else old["baseline_ready"], old["generation"] + int(changed),
                 "첫 확인 대기" if changed else old["last_result"],
                 (utc_now() if changed else after_minutes(interval_minutes)) if old["enabled"] else None,
                 rule_id))

    def toggle_watch(self, rule_id: int, enabled: bool):
        self.toggle_watches((rule_id,), enabled)

    def toggle_watches(self, rule_ids: Iterable[int], enabled: bool):
        due_at = utc_now() if enabled else None
        with self.connect() as con:
            con.executemany("UPDATE watch_rules SET enabled=?,next_due_at=? WHERE id=?",
                            ((int(enabled), due_at, rule_id) for rule_id in rule_ids))

    def delete_watch(self, rule_id: int):
        with self.connect() as con:
            con.execute("DELETE FROM watch_rules WHERE id=?", (rule_id,))

    def due_watches(self) -> list[dict]:
        with self.connect() as con:
            return [dict(x) for x in con.execute("""SELECT * FROM watch_rules
                WHERE enabled=1 AND next_due_at IS NOT NULL AND next_due_at<=? ORDER BY next_due_at""",
                (utc_now(),))]

    def finish_watch(self, rule_id: int, posting_ids: list[str],
                     expected_generation: int | None = None,
                     expected_profile_version: int | None = None) -> list[dict]:
        new_alert_ids = []
        with self.connect() as con:
            rule = con.execute("SELECT * FROM watch_rules WHERE id=?", (rule_id,)).fetchone()
            if not rule or not rule["enabled"]:
                return []
            if ((expected_generation is not None and
                 rule["generation"] != expected_generation) or
                (expected_profile_version is not None and
                 rule["profile_version"] != expected_profile_version)):
                return []
            was_ready = bool(rule["baseline_ready"])
            for posting_id in dict.fromkeys(posting_ids):
                cur = con.execute("INSERT OR IGNORE INTO watch_seen VALUES (?,?)", (rule_id, posting_id))
                if was_ready and cur.rowcount:
                    alert = con.execute("""INSERT INTO alerts(rule_id,generation,query_snapshot,
                        posting_id,created_at,collected_at) VALUES (?,?,?,?,?,?)""",
                        (rule_id, rule["generation"], rule["query"], posting_id, utc_now(),
                         con.execute("SELECT last_watch_collected_at FROM postings WHERE rec_idx=?",
                                     (posting_id,)).fetchone()[0]))
                    new_alert_ids.append(alert.lastrowid)
            message = (f"신규 {len(new_alert_ids)}건 발견" if was_ready else
                       f"기준 {len(posting_ids)}건 등록")
            con.execute("""UPDATE watch_rules SET baseline_ready=1,last_success_at=?,
                next_due_at=?,last_result=? WHERE id=?""",
                (utc_now(), after_minutes(rule["interval_minutes"]), message, rule_id))
            if not new_alert_ids:
                return []
            marks = ",".join("?" for _ in new_alert_ids)
            return [dict(x) for x in con.execute(f"""SELECT a.*,p.company,p.title,p.url,p.favorite,p.provider
                FROM alerts a JOIN postings p ON p.rec_idx=a.posting_id
                WHERE a.id IN ({marks}) ORDER BY a.id DESC""", new_alert_ids)]

    def fail_watch(self, rule_id: int, message: str,
                   expected_generation: int | None = None,
                   expected_profile_version: int | None = None):
        with self.connect() as con:
            rule = con.execute("SELECT * FROM watch_rules WHERE id=?", (rule_id,)).fetchone()
            if rule and (expected_generation is None or rule["generation"] == expected_generation) and (
                    expected_profile_version is None or rule["profile_version"] == expected_profile_version) and rule["enabled"]:
                con.execute("UPDATE watch_rules SET next_due_at=?,last_result=? WHERE id=?",
                            (after_minutes(rule["interval_minutes"]),
                             f"실패: {message[:120]}", rule_id))

    def alerts(self, limit: int = 100) -> list[dict]:
        with self.connect() as con:
            return [dict(x) for x in con.execute("""SELECT a.*,p.company,p.title,p.url,p.favorite,p.provider
                FROM alerts a JOIN postings p ON p.rec_idx=a.posting_id
                ORDER BY a.id DESC LIMIT ?""", (limit,))]

    def mark_alert_read(self, alert_id: int):
        with self.connect() as con:
            con.execute("UPDATE alerts SET read_at=? WHERE id=?", (utc_now(), alert_id))
