from __future__ import annotations

from pathlib import Path
import re
from typing import Any

from radar.extractors.content_extractor import DEFAULT_TIMEOUT, fetch_html
from radar.models import Opportunity, SourceResult
from radar.utils.wechat import extract_wechat_urls, parse_wechat_article_html

FENCED_CODE_RE = re.compile(r"```.*?```", re.DOTALL)


def _load_urls(source: dict[str, Any], project_root: Path) -> list[str]:
    urls: list[str] = []
    for url in source.get("urls", []) or []:
        urls.extend(extract_wechat_urls(str(url)))
    path_value = source.get("path")
    if path_value:
        path = (project_root / path_value).resolve()
        if path.exists():
            text = FENCED_CODE_RE.sub("", path.read_text(encoding="utf-8"))
            urls.extend(extract_wechat_urls(text))
    watchlist_value = source.get("watchlist_path")
    if watchlist_value:
        path = (project_root / watchlist_value).resolve()
        if path.exists():
            text = FENCED_CODE_RE.sub("", path.read_text(encoding="utf-8"))
            urls.extend(extract_wechat_urls(text))
    return [url for url in dict.fromkeys(urls) if "example" not in url and "..." not in url]


def fetch_wechat_articles(source: dict[str, Any], project_root: Path) -> SourceResult:
    result = SourceResult(
        source_id=source["id"],
        source_name=source["name"],
        source_type="wechat_article",
        source_pack=source.get("source_pack", ""),
        source_domain=source.get("domain", ""),
        source_tier=source.get("source_tier", ""),
    )
    try:
        urls = _load_urls(source, project_root)
        max_items = int(source.get("max_items", 20))
        for url in urls[:max_items]:
            html = fetch_html(url, timeout=int(source.get("timeout", DEFAULT_TIMEOUT)))
            parsed = parse_wechat_article_html(html, url)
            account = parsed.get("account") or source.get("name", "微信公众号")
            tags = list(dict.fromkeys([*source.get("tags", []), "微信公众号", account]))
            result.items.append(
                Opportunity(
                    title=parsed["title"],
                    url=parsed["url"],
                    source_id=source["id"],
                    source_name=account,
                    source_group=source.get("group", "wechat"),
                    source_pack=source.get("source_pack", ""),
                    source_domain=source.get("domain", ""),
                    source_tier=source.get("source_tier", ""),
                    published_at=parsed.get("published_at") or None,
                    content=parsed.get("content", ""),
                    summary=parsed.get("summary", ""),
                    category=source.get("category_hint", "微信公众号"),
                    tags=tags,
                    raw={"source_weight": source.get("weight", 1.0), "wechat_account": account},
                )
            )
    except Exception as exc:
        result.error = str(exc)
    return result
