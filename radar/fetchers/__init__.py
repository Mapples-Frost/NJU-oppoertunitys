from __future__ import annotations

from pathlib import Path
from typing import Any

from radar.fetchers.api_fetcher import fetch_api
from radar.fetchers.html_list_fetcher import fetch_html_list
from radar.fetchers.manual_fetcher import fetch_manual
from radar.fetchers.rss_fetcher import fetch_rss
from radar.models import SourceResult


def fetch_source(source: dict[str, Any], project_root: Path) -> SourceResult:
    source_type = source.get("type")
    if source_type == "rss":
        return fetch_rss(source)
    if source_type == "html_list":
        return fetch_html_list(source)
    if source_type == "api":
        return fetch_api(source)
    if source_type == "manual":
        return fetch_manual(source, project_root)
    return SourceResult(
        source_id=source.get("id", "unknown"),
        source_name=source.get("name", "unknown"),
        source_type=str(source_type),
        error=f"unsupported source type: {source_type}",
    )
