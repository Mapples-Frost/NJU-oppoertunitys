from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, time
from zoneinfo import ZoneInfo

import dateparser

from radar.utils.text import normalize_spaces

TZ = ZoneInfo("Asia/Shanghai")
DATE_PATTERNS = [
    re.compile(
        r"(?P<year>20\d{2})[年/-](?P<month>\d{1,2})[月/-](?P<day>\d{1,2})日?"
        r"(?:\s*(?P<hour>\d{1,2})[:：](?P<minute>\d{1,2}))?"
    ),
    re.compile(
        r"(?<!\d)(?P<month>\d{1,2})月(?P<day>\d{1,2})日"
        r"(?:\s*(?P<hour>\d{1,2})[:：](?P<minute>\d{1,2}))?"
    ),
]
ISO_RE = re.compile(r"20\d{2}-\d{1,2}-\d{1,2}(?:\s+\d{1,2}:\d{2})?")
DEADLINE_HINTS = ("截止", "报名", "提交", "申报", "申请", "征集", "至", "结束")
EVENT_HINTS = ("讲座", "报告", "活动", "比赛", "初赛", "决赛", "开营", "时间")


@dataclass
class DateCandidate:
    value: datetime
    source_text: str
    has_year: bool
    hint_score: int
    rolled_year: bool = False


def _build_datetime(match: re.Match[str], now: datetime) -> tuple[datetime | None, bool]:
    groups = match.groupdict()
    year_text = groups.get("year")
    year = int(year_text) if year_text else now.year
    month = int(groups["month"])
    day = int(groups["day"])
    hour = int(groups.get("hour") or 23)
    minute = int(groups.get("minute") or 59)
    try:
        return datetime.combine(
            datetime(year, month, day, tzinfo=TZ).date(),
            time(hour=min(hour, 23), minute=min(minute, 59)),
            tzinfo=TZ,
        ), bool(year_text)
    except ValueError:
        return None, bool(year_text)


def _hint_score(context: str, hints: tuple[str, ...]) -> int:
    score = 0
    for hint in hints:
        if hint in context:
            score += 2 if hint in DEADLINE_HINTS else 1
    return score


def _collect_candidates(text: str, now: datetime, hints: tuple[str, ...]) -> list[DateCandidate]:
    candidates: list[DateCandidate] = []
    normalized = normalize_spaces(text)
    for pattern in DATE_PATTERNS:
        for match in pattern.finditer(normalized):
            value, has_year = _build_datetime(match, now)
            if not value:
                continue
            start, end = match.span()
            context = normalized[max(0, start - 20) : min(len(normalized), end + 20)]
            rolled = False
            if value.date() < now.date():
                value = value.replace(year=value.year + 1)
                rolled = True
            candidates.append(
                DateCandidate(
                    value=value,
                    source_text=context,
                    has_year=has_year,
                    hint_score=_hint_score(context, hints),
                    rolled_year=rolled,
                )
            )
    for match in ISO_RE.finditer(normalized):
        parsed = dateparser.parse(match.group(0), languages=["zh", "en"], settings={"TIMEZONE": "Asia/Shanghai"})
        if not parsed:
            continue
        value = parsed.replace(tzinfo=TZ) if parsed.tzinfo is None else parsed.astimezone(TZ)
        start, end = match.span()
        context = normalized[max(0, start - 20) : min(len(normalized), end + 20)]
        rolled = False
        if value.date() < now.date():
            value = value.replace(year=value.year + 1)
            rolled = True
        candidates.append(
            DateCandidate(
                value=value,
                source_text=context,
                has_year=True,
                hint_score=_hint_score(context, hints),
                rolled_year=rolled,
            )
        )
    return candidates


def _select(candidates: list[DateCandidate]) -> DateCandidate | None:
    if not candidates:
        return None
    return sorted(candidates, key=lambda item: (item.hint_score, item.value), reverse=True)[0]


def extract_dates(title: str, content: str, now: datetime | None = None) -> dict[str, str | None]:
    now = now.astimezone(TZ) if now else datetime.now(TZ)
    text = f"{title}\n{content}"
    deadline = _select(_collect_candidates(text, now, DEADLINE_HINTS))
    event = _select(_collect_candidates(text, now, EVENT_HINTS))

    confidence = None
    source_text = None
    if deadline:
        if deadline.rolled_year:
            confidence = "low"
        elif deadline.hint_score > 0 and deadline.has_year:
            confidence = "high"
        elif deadline.hint_score > 0:
            confidence = "medium"
        else:
            confidence = "low"
        source_text = deadline.source_text

    return {
        "deadline_at": deadline.value.isoformat(timespec="seconds") if deadline else None,
        "event_start_at": event.value.isoformat(timespec="seconds") if event else None,
        "event_end_at": None,
        "date_confidence": confidence,
        "date_source_text": source_text,
    }
