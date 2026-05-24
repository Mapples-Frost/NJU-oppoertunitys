from __future__ import annotations

from typing import Any

from radar.fetchers.html_list_fetcher import fetch_html_list
from radar.models import SourceResult


def fetch_playwright_html(source: dict[str, Any]) -> SourceResult:
    # Optional V2 capability: if Playwright is not installed, degrade cleanly.
    try:
        import playwright  # noqa: F401
    except Exception:
        return SourceResult(
            source_id=source.get("id", "unknown"),
            source_name=source.get("name", "unknown"),
            source_type="playwright_html",
            source_pack=source.get("source_pack", ""),
            source_domain=source.get("domain", ""),
            source_tier=source.get("source_tier", ""),
            error="playwright is not installed; this public dynamic source is skipped",
        )
    # The first V2 implementation keeps the interface in place and falls back to
    # the static parser until per-site browser selectors are tuned.
    return fetch_html_list({**source, "type": "html_list"})
