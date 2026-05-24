from __future__ import annotations

import re
from html import unescape


_SPACE_RE = re.compile(r"\s+")
_DATE_RE = re.compile(
    r"(?:(?:20\d{2})[年/\-.])?\d{1,2}[月/\-.]\d{1,2}日?"
    r"|(?:20\d{2})年"
)
_BOILERPLATE_RE = re.compile(
    r"(关于|举办|举行|开展|组织|申报|报名|开启|启动|通知|公告|的|：|:|—|-|\[|\]|【|】)"
)


def normalize_spaces(value: str | None) -> str:
    if not value:
        return ""
    return _SPACE_RE.sub(" ", unescape(value)).strip()


def compact_text(value: str | None) -> str:
    return normalize_spaces(value).replace(" ", "")


def clean_title(title: str) -> str:
    value = normalize_spaces(title).lower()
    value = _DATE_RE.sub("", value)
    value = _BOILERPLATE_RE.sub("", value)
    value = re.sub(r"[^\w\u4e00-\u9fff]+", "", value)
    return value.strip()


def first_sentence(text: str, limit: int = 180) -> str:
    value = normalize_spaces(text)
    if not value:
        return ""
    parts = re.split(r"(?<=[。！？!?])", value, maxsplit=1)
    summary = parts[0] if parts and parts[0] else value
    if len(summary) > limit:
        return summary[: limit - 1].rstrip() + "…"
    return summary
