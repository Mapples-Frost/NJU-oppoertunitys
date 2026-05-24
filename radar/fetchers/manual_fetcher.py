from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from radar.models import Opportunity, SourceResult
from radar.utils.text import normalize_spaces
from radar.utils.url import canonicalize_url

LABEL_RE = re.compile(r"^(?P<label>链接|来源|内容|截止|时间|备注)\s*[:：]\s*(?P<value>.+)$")
FENCED_CODE_RE = re.compile(r"```.*?```", re.DOTALL)


def _parse_section(section: str, source: dict[str, Any]) -> Opportunity | None:
    lines = [line.strip() for line in section.splitlines() if line.strip()]
    if not lines or not lines[0].startswith("##"):
        return None
    title = normalize_spaces(lines[0].lstrip("#").strip())
    values: dict[str, list[str]] = {}
    body_lines: list[str] = []
    for line in lines[1:]:
        match = LABEL_RE.match(line)
        if match:
            values.setdefault(match.group("label"), []).append(match.group("value").strip())
        else:
            body_lines.append(line)
    content_parts = values.get("内容", []) + body_lines + values.get("备注", [])
    deadline_text = " ".join(values.get("截止", []) + values.get("时间", []))
    if deadline_text:
        content_parts.append(f"截止：{deadline_text}")
    url = canonicalize_url(values.get("链接", [""])[0])
    return Opportunity(
        title=title,
        url=url,
        source_id=source["id"],
        source_name=source["name"],
        source_group=source.get("group", "manual"),
        content=normalize_spaces(" ".join(content_parts)),
        category=source.get("category_hint", "手动入口"),
        tags=list(source.get("tags", [])),
        raw={
            "manual_source": " ".join(values.get("来源", [])),
            "source_weight": source.get("weight", 1.0),
        },
    )


def parse_manual_markdown(text: str, source: dict[str, Any]) -> list[Opportunity]:
    text = FENCED_CODE_RE.sub("", text)
    sections = re.split(r"(?=^##\s+)", text, flags=re.MULTILINE)
    items: list[Opportunity] = []
    for section in sections:
        item = _parse_section(section, source)
        if item:
            items.append(item)
    return items


def fetch_manual(source: dict[str, Any], project_root: Path) -> SourceResult:
    source_id = source["id"]
    source_name = source["name"]
    result = SourceResult(source_id=source_id, source_name=source_name, source_type="manual")
    try:
        path = (project_root / source.get("path", "inbox/manual.md")).resolve()
        if not path.exists():
            result.items = []
            return result
        result.items = parse_manual_markdown(path.read_text(encoding="utf-8"), source)
    except Exception as exc:
        result.error = str(exc)
    return result
