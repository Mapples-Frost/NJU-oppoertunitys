from __future__ import annotations

from typing import Any

import requests

from radar.extractors.content_extractor import DEFAULT_TIMEOUT, HEADERS, get_nested
from radar.models import Opportunity, SourceResult
from radar.utils.text import normalize_spaces
from radar.utils.url import canonicalize_url


def fetch_api(source: dict[str, Any]) -> SourceResult:
    source_id = source["id"]
    source_name = source["name"]
    result = SourceResult(source_id=source_id, source_name=source_name, source_type="api")
    try:
        response = requests.request(
            source.get("method", "GET"),
            source["url"],
            headers={**HEADERS, **source.get("headers", {})},
            timeout=int(source.get("timeout", DEFAULT_TIMEOUT)),
        )
        response.raise_for_status()
        payload = response.json()
        items = get_nested(payload, source.get("items_path"), [])
        if not isinstance(items, list):
            raise ValueError("items_path did not resolve to a list")
        max_items = int(source.get("max_items", 10))
        for item in items[:max_items]:
            title = normalize_spaces(str(get_nested(item, source.get("title_path"), "")))
            if not title:
                continue
            link = get_nested(item, source.get("link_path"), "")
            content = normalize_spaces(str(get_nested(item, source.get("content_path"), "")))
            result.items.append(
                Opportunity(
                    title=title,
                    url=canonicalize_url(str(link), source.get("base_url") or source["url"]),
                    source_id=source_id,
                    source_name=source_name,
                    source_group=source.get("group", ""),
                    published_at=normalize_spaces(str(get_nested(item, source.get("date_path"), ""))) or None,
                    content=content,
                    category=source.get("category_hint", ""),
                    tags=list(source.get("tags", [])),
                    raw={"source_weight": source.get("weight", 1.0)},
                )
            )
    except Exception as exc:
        result.error = str(exc)
    return result
