from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from rapidfuzz import fuzz

from radar.models import Opportunity, RunSummary
from radar.storage.migrations import REQUIRED_COLUMNS, SCHEMA
from radar.utils.text import clean_title


class Database:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row

    def close(self) -> None:
        self.conn.close()

    def migrate(self) -> None:
        deferred_indexes: list[str] = []
        for statement in SCHEMA:
            if statement.strip().upper().startswith("CREATE INDEX"):
                deferred_indexes.append(statement)
            else:
                self.conn.execute(statement)
        self._ensure_columns()
        for statement in deferred_indexes:
            self.conn.execute(statement)
        self.conn.commit()

    def _ensure_columns(self) -> None:
        for table, columns in REQUIRED_COLUMNS.items():
            existing = {
                str(row["name"])
                for row in self.conn.execute(f"PRAGMA table_info({table})").fetchall()
            }
            for column, definition in columns.items():
                if column not in existing:
                    self.conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

    def upsert_source(self, source: dict[str, Any], success: bool, error: str | None, total_found: int) -> None:
        now = datetime.now().astimezone().isoformat(timespec="seconds")
        existing = self.conn.execute("SELECT id FROM sources WHERE id = ?", (source["id"],)).fetchone()
        if existing:
            self.conn.execute(
                """
                UPDATE sources
                SET name = ?, type = ?, source_pack = ?, domain = ?, source_tier = ?, enabled = ?,
                    last_success_at = COALESCE(?, last_success_at),
                    last_error_at = COALESCE(?, last_error_at), last_error = ?, total_found = ?,
                    success_count = success_count + ?,
                    failure_count = failure_count + ?,
                    consecutive_failures = CASE WHEN ? = 1 THEN 0 ELSE consecutive_failures + 1 END
                WHERE id = ?
                """,
                (
                    source.get("name"),
                    source.get("type"),
                    source.get("source_pack"),
                    source.get("domain"),
                    source.get("source_tier"),
                    int(source.get("enabled", True)),
                    now if success else None,
                    now if not success else None,
                    error,
                    total_found,
                    1 if success else 0,
                    0 if success else 1,
                    1 if success else 0,
                    source["id"],
                ),
            )
        else:
            self.conn.execute(
                """
                INSERT INTO sources
                (id, name, type, source_pack, domain, source_tier, enabled, last_success_at, last_error_at,
                 last_error, success_count, failure_count, consecutive_failures, total_found)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    source["id"],
                    source.get("name"),
                    source.get("type"),
                    source.get("source_pack"),
                    source.get("domain"),
                    source.get("source_tier"),
                    int(source.get("enabled", True)),
                    now if success else None,
                    now if not success else None,
                    error,
                    1 if success else 0,
                    0 if success else 1,
                    0 if success else 1,
                    total_found,
                ),
            )
        self.conn.commit()

    def insert_source_run(
        self,
        run_id: str,
        source: dict[str, Any],
        status: str,
        items_found: int,
        error: str | None,
        started_at: str,
        finished_at: str,
    ) -> None:
        row_id = f"{run_id}:{source['id']}"
        self.conn.execute(
            """
            INSERT OR REPLACE INTO source_runs
            (id, run_id, source_id, source_name, source_pack, domain, source_tier, status,
             items_found, error, started_at, finished_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row_id,
                run_id,
                source["id"],
                source.get("name"),
                source.get("source_pack"),
                source.get("domain"),
                source.get("source_tier"),
                status,
                items_found,
                error,
                started_at,
                finished_at,
            ),
        )
        self.conn.commit()

    def insert_run(self, run: RunSummary) -> None:
        self.conn.execute(
            """
            INSERT OR REPLACE INTO runs
            (id, started_at, finished_at, status, total_sources, successful_sources, failed_sources,
             total_items, new_items, emailed_items, pack_stats)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run.id,
                run.started_at,
                run.finished_at,
                run.status,
                run.total_sources,
                run.successful_sources,
                run.failed_sources,
                run.total_items,
                run.new_items,
                run.emailed_items,
                json.dumps(run.pack_stats, ensure_ascii=False),
            ),
        )
        self.conn.commit()

    def _dedup_match(self, opportunity: Opportunity) -> str | None:
        keys = [
            (opportunity.url_hash, "url"),
            (opportunity.title_hash, "title"),
            (opportunity.content_hash, "content"),
        ]
        for key, _key_type in keys:
            if not key:
                continue
            row = self.conn.execute("SELECT opportunity_id FROM dedup_index WHERE key = ?", (key,)).fetchone()
            if row:
                return str(row["opportunity_id"])
        cleaned = clean_title(opportunity.title)
        if cleaned:
            rows = self.conn.execute(
                "SELECT id, title FROM opportunities ORDER BY discovered_at DESC LIMIT 500"
            ).fetchall()
            for row in rows:
                if fuzz.token_set_ratio(cleaned, clean_title(str(row["title"]))) >= 88:
                    return str(row["id"])
        return None

    def upsert_opportunity(self, opportunity: Opportunity) -> bool:
        existing_id = self._dedup_match(opportunity)
        is_new = existing_id is None
        if existing_id:
            opportunity.id = existing_id
            row = self.conn.execute("SELECT discovered_at FROM opportunities WHERE id = ?", (existing_id,)).fetchone()
            if row:
                opportunity.discovered_at = str(row["discovered_at"])
        columns = list(opportunity.to_db_row().keys())
        values = opportunity.to_db_row()
        placeholders = ", ".join(f":{column}" for column in columns)
        update_columns = [column for column in columns if column != "id"]
        updates = ", ".join(f"{column} = excluded.{column}" for column in update_columns)
        self.conn.execute(
            f"""
            INSERT INTO opportunities ({", ".join(columns)})
            VALUES ({placeholders})
            ON CONFLICT(id) DO UPDATE SET {updates}
            """,
            values,
        )
        self._insert_dedup(opportunity)
        self.conn.commit()
        return is_new

    def _insert_dedup(self, opportunity: Opportunity) -> None:
        now = datetime.now().astimezone().isoformat(timespec="seconds")
        for key, key_type in [
            (opportunity.url_hash, "url"),
            (opportunity.title_hash, "title"),
            (opportunity.content_hash, "content"),
        ]:
            if key:
                self.conn.execute(
                    """
                    INSERT OR IGNORE INTO dedup_index (key, opportunity_id, key_type, created_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (key, opportunity.id, key_type, now),
                )
