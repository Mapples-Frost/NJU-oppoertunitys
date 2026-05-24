from __future__ import annotations

from pathlib import Path
from typing import Any

from radar.fetchers.api_fetcher import fetch_api
from radar.fetchers.html_list_fetcher import fetch_html_list
from radar.fetchers.imap_email_fetcher import fetch_imap_email
from radar.fetchers.manual_fetcher import fetch_manual
from radar.fetchers.playwright_html_fetcher import fetch_playwright_html
from radar.fetchers.rss_fetcher import fetch_rss
from radar.fetchers.sitemap_fetcher import fetch_sitemap
from radar.fetchers.webhook_inbox_fetcher import fetch_webhook_inbox
from radar.fetchers.wechat_article_fetcher import fetch_wechat_articles
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
    if source_type == "wechat_article":
        return fetch_wechat_articles(source, project_root)
    if source_type == "imap_email":
        return fetch_imap_email(source)
    if source_type == "webhook_inbox":
        return fetch_webhook_inbox(source, project_root)
    if source_type == "sitemap":
        return fetch_sitemap(source)
    if source_type == "playwright_html":
        return fetch_playwright_html(source)
    return SourceResult(
        source_id=source.get("id", "unknown"),
        source_name=source.get("name", "unknown"),
        source_type=str(source_type),
        error=f"unsupported source type: {source_type}",
    )
