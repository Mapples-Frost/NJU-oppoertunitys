from __future__ import annotations

SCHEMA = [
    """
    CREATE TABLE IF NOT EXISTS opportunities (
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
    """,
    """
    CREATE TABLE IF NOT EXISTS sources (
        id TEXT PRIMARY KEY,
        name TEXT,
        type TEXT,
        enabled INTEGER,
        last_success_at TEXT,
        last_error_at TEXT,
        last_error TEXT,
        total_found INTEGER DEFAULT 0
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS runs (
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
    """,
    """
    CREATE TABLE IF NOT EXISTS dedup_index (
        key TEXT PRIMARY KEY,
        opportunity_id TEXT,
        key_type TEXT,
        created_at TEXT
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_opportunities_score ON opportunities(score)",
    "CREATE INDEX IF NOT EXISTS idx_opportunities_deadline ON opportunities(deadline_at)",
    "CREATE INDEX IF NOT EXISTS idx_opportunities_title_hash ON opportunities(title_hash)",
]
