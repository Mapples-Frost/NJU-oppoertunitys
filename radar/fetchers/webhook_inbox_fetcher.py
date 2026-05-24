from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from radar.models import Opportunity, SourceResult
from radar.utils.text import normalize_spaces
from radar.utils.url import canonicalize_url
from radar.utils.wechat import extract_wechat_urls


def fetch_webhook_inbox(source: dict[str, Any], project_root: Path) -> SourceResult:
    result = SourceResult(
        source_id=source["id"],
        source_name=source["name"],
        source_type="webhook_inbox",
        source_pack=source.get("source_pack", ""),
        source_domain=source.get("domain", ""),
        source_tier=source.get("source_tier", ""),
    )
    try:
        path = (project_root / source.get("path", "inbox/webhook_inbox.jsonl")).resolve()
        if not path.exists():
            return result
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            payload = json.loads(line)
            text = " ".join(str(payload.get(key, "")) for key in ["title", "url", "content", "summary"])
            wechat_urls = extract_wechat_urls(text)
            url = wechat_urls[0] if wechat_urls else canonicalize_url(str(payload.get("url", "")))
            title = normalize_spaces(str(payload.get("title", ""))) or "Webhook 转发机会"
            content = normalize_spaces(str(payload.get("content") or payload.get("summary") or text))
            result.items.append(
                Opportunity(
                    title=title,
                    url=url,
                    source_id=source["id"],
                    source_name=str(payload.get("source") or source["name"]),
                    source_group=source.get("group", "webhook"),
                    source_pack=source.get("source_pack", ""),
                    source_domain=source.get("domain", ""),
                    source_tier=source.get("source_tier", ""),
                    content=content,
                    category=source.get("category_hint", "Webhook 转发"),
                    tags=list(source.get("tags", [])),
                    raw={"source_weight": source.get("weight", 1.0), "payload": payload},
                )
            )
    except Exception as exc:
        result.error = str(exc)
    return result
