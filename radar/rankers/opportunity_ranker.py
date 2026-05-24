from __future__ import annotations

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from radar.models import Opportunity

TZ = ZoneInfo("Asia/Shanghai")


def _contains_any(text: str, words: list[str]) -> bool:
    lower = text.lower()
    return any(word.lower() in lower for word in words)


def _keyword_score(text: str, keywords: dict[str, Any], scoring: dict[str, Any]) -> float:
    weights = scoring.get("keyword_weights", {"high": 40, "medium": 24, "low": 10})
    positive = keywords.get("positive", {})
    score = 0.0
    for tier, words in positive.items():
        matches = sum(1 for word in words if word.lower() in text.lower())
        score += min(float(weights.get(tier, 0)), matches * float(weights.get(tier, 0)) / 2)
    if _contains_any(text, keywords.get("negative", [])):
        score -= float(scoring.get("negative_penalty", 18))
    return max(0.0, min(40.0, score))


def _organizer_score(text: str, source_group: str, scoring: dict[str, Any]) -> float:
    top = scoring.get("organizers", {}).get("top", [])
    medium = scoring.get("organizers", {}).get("medium", [])
    if _contains_any(text, top):
        return 20.0
    if source_group in {"nju", "academic"} or _contains_any(text, medium):
        return 14.0
    if source_group in {"competition", "enterprise"}:
        return 12.0
    if source_group == "manual":
        return 8.0
    return 6.0


def _output_value_score(text: str) -> float:
    high = ["奖", "奖金", "证书", "项目", "作品", "代码", "论文", "实习", "offer", "晋级"]
    medium = ["训练营", "夏令营", "课程", "培训", "简历", "实践"]
    if _contains_any(text, high):
        return 15.0
    if _contains_any(text, medium):
        return 10.0
    if _contains_any(text, ["讲座", "报告", "沙龙"]):
        return 5.0
    return 3.0


def _deadline_score(deadline_at: str | None, now: datetime | None = None) -> float:
    if not deadline_at:
        return 3.0
    now = now.astimezone(TZ) if now else datetime.now(TZ)
    try:
        deadline = datetime.fromisoformat(deadline_at)
        if deadline.tzinfo is None:
            deadline = deadline.replace(tzinfo=TZ)
        days = (deadline.astimezone(TZ).date() - now.date()).days
    except ValueError:
        return 3.0
    if days < 0:
        return 0.0
    if days <= 3:
        return 10.0
    if days <= 7:
        return 8.0
    if days <= 30:
        return 6.0
    return 4.0


def rank(opportunity: Opportunity, keywords: dict[str, Any], scoring: dict[str, Any]) -> Opportunity:
    primary_text = " ".join(part for part in [opportunity.title, opportunity.content] if part)
    tag_text = " ".join(opportunity.tags)
    combined_text = f"{primary_text} {tag_text}"
    source_weight = float(opportunity.raw.get("source_weight", 1.0))
    relevance = _keyword_score(primary_text, keywords, scoring)
    tag_bonus = min(8.0, _keyword_score(tag_text, keywords, scoring) / 5)
    opportunity_markers = ["竞赛", "大赛", "挑战赛", "报名", "讲座", "报告", "训练营", "项目", "招募", "活动"]
    if not _contains_any(primary_text, opportunity_markers):
        tag_bonus = min(tag_bonus, 4.0)
    relevance = min(40.0, relevance + tag_bonus)
    organizer = _organizer_score(combined_text, opportunity.source_group, scoring)
    output_value = _output_value_score(primary_text)
    deadline = _deadline_score(opportunity.deadline_at)
    source = min(10.0, max(0.0, 8.0 * source_weight))
    novelty = 5.0
    total = relevance + organizer + output_value + deadline + source + novelty
    opportunity.relevance_score = round(relevance, 2)
    opportunity.organizer_score = round(organizer + output_value + source, 2)
    opportunity.deadline_score = round(deadline, 2)
    opportunity.novelty_score = round(novelty, 2)
    opportunity.score = round(max(0.0, min(100.0, total)), 2)
    return opportunity
