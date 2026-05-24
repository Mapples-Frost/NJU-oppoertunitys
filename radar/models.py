from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class Opportunity:
    title: str
    source_id: str
    source_name: str
    source_group: str
    url: str | None = None
    published_at: str | None = None
    discovered_at: str | None = None
    deadline_at: str | None = None
    event_start_at: str | None = None
    event_end_at: str | None = None
    date_confidence: str | None = None
    date_source_text: str | None = None
    content: str = ""
    summary: str = ""
    category: str = ""
    tags: list[str] = field(default_factory=list)
    score: float = 0.0
    relevance_score: float = 0.0
    organizer_score: float = 0.0
    deadline_score: float = 0.0
    novelty_score: float = 0.0
    status: str = "new"
    content_hash: str = ""
    title_hash: str = ""
    url_hash: str = ""
    id: str = ""
    recommended_action: str = ""
    raw: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.discovered_at:
            self.discovered_at = datetime.now().astimezone().isoformat(timespec="seconds")

    @property
    def combined_text(self) -> str:
        return " ".join(part for part in [self.title, self.content, " ".join(self.tags)] if part)

    def to_db_row(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "url": self.url,
            "source_id": self.source_id,
            "source_name": self.source_name,
            "source_group": self.source_group,
            "published_at": self.published_at,
            "discovered_at": self.discovered_at,
            "deadline_at": self.deadline_at,
            "event_start_at": self.event_start_at,
            "event_end_at": self.event_end_at,
            "date_confidence": self.date_confidence,
            "date_source_text": self.date_source_text,
            "content": self.content,
            "summary": self.summary,
            "category": self.category,
            "tags": ",".join(self.tags),
            "score": self.score,
            "relevance_score": self.relevance_score,
            "organizer_score": self.organizer_score,
            "deadline_score": self.deadline_score,
            "novelty_score": self.novelty_score,
            "status": self.status,
            "content_hash": self.content_hash,
            "title_hash": self.title_hash,
            "url_hash": self.url_hash,
        }


@dataclass
class SourceResult:
    source_id: str
    source_name: str
    source_type: str
    items: list[Opportunity] = field(default_factory=list)
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None


@dataclass
class RunSummary:
    id: str
    started_at: str
    finished_at: str | None = None
    status: str = "running"
    total_sources: int = 0
    successful_sources: int = 0
    failed_sources: int = 0
    total_items: int = 0
    new_items: int = 0
    emailed_items: int = 0
    errors: list[dict[str, str]] = field(default_factory=list)
