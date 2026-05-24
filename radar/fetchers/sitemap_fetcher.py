from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Any

from radar.extractors.content_extractor import DEFAULT_TIMEOUT, fetch_and_extract, fetch_html
from radar.models import Opportunity, SourceResult
from radar.utils.text import normalize_spaces
from radar.utils.url import canonicalize_url


def fetch_sitemap(source: dict[str, Any]) -> SourceResult:
    result = SourceResult(
        source_id=source["id"],
        source_name=source["name"],
        source_type="sitemap",
        source_pack=source.get("source_pack", ""),
        source_domain=source.get("domain", ""),
        source_tier=source.get("source_tier", ""),
    )
    try:
        xml_text = fetch_html(source["sitemap_url"], timeout=int(source.get("timeout", DEFAULT_TIMEOUT)))
        root = ET.fromstring(xml_text)
        namespace = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
        urls = []
        for loc in root.findall(f".//{namespace}loc") + root.findall(".//loc"):
            if loc.text:
                urls.append(canonicalize_url(loc.text))
        include_keywords = source.get("include_url_keywords", [])
        if include_keywords:
            urls = [url for url in urls if any(keyword.lower() in url.lower() for keyword in include_keywords)]
        for url in list(dict.fromkeys(urls))[: int(source.get("max_items", 10))]:
            title = url.rstrip("/").split("/")[-1].replace("-", " ").replace("_", " ") or source["name"]
            content = ""
            if source.get("detail_required", False):
                try:
                    content = fetch_and_extract(url, selector=source.get("detail_content_selector"))
                except Exception:
                    content = title
            result.items.append(
                Opportunity(
                    title=normalize_spaces(title),
                    url=url,
                    source_id=source["id"],
                    source_name=source["name"],
                    source_group=source.get("group", ""),
                    source_pack=source.get("source_pack", ""),
                    source_domain=source.get("domain", ""),
                    source_tier=source.get("source_tier", ""),
                    content=content,
                    category=source.get("category_hint", ""),
                    tags=list(source.get("tags", [])),
                    raw={"source_weight": source.get("weight", 1.0)},
                )
            )
    except Exception as exc:
        result.error = str(exc)
    return result
