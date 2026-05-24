from pathlib import Path

from radar.models import RunSummary
from radar.storage.db import Database


def test_database_migration_adds_v2_tables_and_columns(tmp_path: Path):
    db = Database(tmp_path / "test.sqlite")
    db.migrate()

    source_columns = {row["name"] for row in db.conn.execute("PRAGMA table_info(sources)").fetchall()}
    opportunity_columns = {row["name"] for row in db.conn.execute("PRAGMA table_info(opportunities)").fetchall()}
    tables = {row["name"] for row in db.conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}

    assert "source_pack" in source_columns
    assert "source_pack" in opportunity_columns
    assert "source_runs" in tables
    assert "http_cache" in tables

    run = RunSummary(
        id="run",
        started_at="2026-05-24T08:00:00+08:00",
        pack_stats={"wechat_pack": {"total": 1, "successful": 1, "failed": 0, "items": 0, "new_items": 0}},
    )
    db.insert_run(run)
    stored = db.conn.execute("SELECT pack_stats FROM runs WHERE id = 'run'").fetchone()["pack_stats"]
    assert "wechat_pack" in stored
    db.close()


def test_database_migration_upgrades_existing_v1_database(tmp_path: Path):
    db_path = tmp_path / "v1.sqlite"
    db = Database(db_path)
    db.conn.execute(
        """
        CREATE TABLE opportunities (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            url TEXT,
            source_id TEXT,
            source_name TEXT,
            source_group TEXT,
            published_at TEXT,
            discovered_at TEXT NOT NULL,
            deadline_at TEXT,
            event_start_at TEXT,
            event_end_at TEXT,
            date_confidence TEXT,
            date_source_text TEXT,
            content TEXT,
            summary TEXT,
            category TEXT,
            tags TEXT,
            score REAL,
            relevance_score REAL,
            organizer_score REAL,
            deadline_score REAL,
            novelty_score REAL,
            status TEXT DEFAULT 'new',
            content_hash TEXT,
            title_hash TEXT,
            url_hash TEXT
        )
        """
    )
    db.conn.execute(
        """
        CREATE TABLE sources (
            id TEXT PRIMARY KEY,
            name TEXT,
            type TEXT,
            enabled INTEGER,
            last_success_at TEXT,
            last_error_at TEXT,
            last_error TEXT,
            total_found INTEGER DEFAULT 0
        )
        """
    )
    db.conn.execute(
        """
        CREATE TABLE runs (
            id TEXT PRIMARY KEY,
            started_at TEXT,
            finished_at TEXT,
            status TEXT,
            total_sources INTEGER,
            successful_sources INTEGER,
            failed_sources INTEGER,
            total_items INTEGER,
            new_items INTEGER,
            emailed_items INTEGER
        )
        """
    )
    db.conn.commit()

    db.migrate()

    source_columns = {row["name"] for row in db.conn.execute("PRAGMA table_info(sources)").fetchall()}
    opportunity_columns = {row["name"] for row in db.conn.execute("PRAGMA table_info(opportunities)").fetchall()}
    run_columns = {row["name"] for row in db.conn.execute("PRAGMA table_info(runs)").fetchall()}
    assert "source_pack" in source_columns
    assert "source_pack" in opportunity_columns
    assert "pack_stats" in run_columns
    db.close()
