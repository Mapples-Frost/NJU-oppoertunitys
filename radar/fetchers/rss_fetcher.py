from __future__ import annotations

from datetime import datetime
from email.utils import parsedate_to_datetime
from typing import Any

import feedparser

from radar.models import Opportunity, SourceResult
from radar.utils.text import normalize_spaces
from radar.utils.url import canonicalize_url


def _entry_datetime(entry: Any) -> str | None:
    for key in ("published", "updated", "created"):
        value = entry.get(key)
        if value:
            try:
                return parsedate_to_datetime(value).astimezone().isoformat(timespec="seconds")
            except Exception:
                return normalize_spaces(str(value))
    return None


def _entry_content(entry: Any) -> str:
    chunks: list[str] = []
    if entry.get("summary"):
        chunks.append(str(entry.get("summary")))
    for content_item in entry.get("content", []) or []:
        value = content_item.get("value") if isinstance(content_item, dict) else None
        if value:
            chunks.append(str(value))
    return normalize_spaces(" ".join(chunks))


def fetch_rss(source: dict[str, Any]) -> SourceResult:
    source_id = source["id"]
    source_name = source["name"]
    result = SourceResult(source_id=source_id, source_name=source_name, source_type="rss")
    try:
        feed = feedparser.parse(source["feed_url"])
        if getattr(feed, "bozo", False) and not feed.entries:
            raise RuntimeError(str(getattr(feed, "bozo_exception", "invalid feed")))
        max_items = int(source.get("max_items", 10))
        for entry in feed.entries[:max_items]:
            title = normalize_spaces(entry.get("title", ""))
            if not title:
                continue
            result.items.append(
                Opportunity(
                    title=title,
                    url=canonicalize_url(entry.get("link")),
                    source_id=source_id,
                    source_name=source_name,
                    source_group=source.get("group", ""),
                    published_at=_entry_datetime(entry) or datetime.now().astimezone().isoformat(timespec="seconds"),
                    content=_entry_content(entry),
                    category=source.get("category_hint", ""),
                    tags=list(source.get("tags", [])),
                    raw={"source_weight": source.get("weight", 1.0)},
                )
            )
    except Exception as exc:
        result.error = str(exc)
    return result
