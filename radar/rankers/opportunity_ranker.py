from __future__ import annotations

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from radar.models import Opportunity

TZ = ZoneInfo("Asia/Shanghai")


def _contains_any(text: str, words: list[str]) -> bool:
    lower = text.lower()
    return any(word.lower() in lower for word in words)


def _keyword_score(text: str, keywords: dict[str, Any], scoring: dict[str, Any], quality: dict[str, Any] | None = None) -> float:
    weights = scoring.get("keyword_weights", {"high": 40, "medium": 24, "low": 10})
    positive = keywords.get("positive", {})
    background_terms = set(word.lower() for word in (quality or {}).get("background_terms", []))
    score = 0.0
    lower_text = text.lower()
    for tier, words in positive.items():
        tier_weight = float(weights.get(tier, 0))
        matches = 0
        for word in words:
            if word.lower() not in lower_text:
                continue
            if word.lower() in background_terms:
                score += min(2.0, tier_weight / 12)
            else:
                matches += 1
        score += min(tier_weight, matches * tier_weight / 2)
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


def _fallback_actionability(text: str, deadline_at: str | None) -> float:
    markers = [
        "竞赛",
        "大赛",
        "挑战赛",
        "报名",
        "申报",
        "投稿",
        "征集",
        "招募",
        "赛题",
        "申请",
        "competition",
        "challenge",
        "cfp",
        "call for papers",
        "application",
        "deadline",
        "submit",
    ]
    score = min(22.0, sum(1 for marker in markers if marker.lower() in text.lower()) * 5.0)
    if deadline_at:
        score += 8.0
    return min(30.0, score)


def rank(
    opportunity: Opportunity,
    keywords: dict[str, Any],
    scoring: dict[str, Any],
    profile: dict[str, Any] | None = None,
    quality: dict[str, Any] | None = None,
    feedback: dict[str, Any] | None = None,
) -> Opportunity:
    primary_text = " ".join(part for part in [opportunity.title, opportunity.content] if part)
    tag_text = " ".join(opportunity.tags)
    combined_text = f"{primary_text} {tag_text}"
    source_weight = float(opportunity.raw.get("source_weight", 1.0))

    relevance_raw = _keyword_score(primary_text, keywords, scoring, quality)
    tag_bonus = min(6.0, _keyword_score(tag_text, keywords, scoring, quality) / 6)
    opportunity_markers = [
        "竞赛",
        "大赛",
        "挑战赛",
        "报名",
        "申报",
        "投稿",
        "招募",
        "赛题",
        "CFP",
        "competition",
        "challenge",
        "deadline",
        "application",
        "proposal",
    ]
    if not _contains_any(primary_text, opportunity_markers):
        tag_bonus = min(tag_bonus, 2.0)
    relevance = min(30.0, relevance_raw * 0.65 + tag_bonus + min(opportunity.audience_fit_score, 8.0))
    actionability = min(25.0, opportunity.actionability_score or _fallback_actionability(primary_text, opportunity.deadline_at))
    audience_fit = min(14.0, opportunity.audience_fit_score / 2 if opportunity.audience_fit_score else 0.0)
    organizer = min(10.0, _organizer_score(combined_text, opportunity.source_group, scoring) / 2)
    output_value = min(8.0, _output_value_score(primary_text) / 2)
    deadline = _deadline_score(opportunity.deadline_at)
    source = min(7.0, max(0.0, 5.5 * source_weight))
    if feedback and (
        opportunity.source_id in set(feedback.get("prefer_sources", []))
        or opportunity.source_name in set(feedback.get("prefer_sources", []))
    ):
        source += 3.0
    quality_bonus = min(6.0, opportunity.quality_score / 12 if opportunity.quality_score else 0.0)
    novelty = 5.0
    total = relevance + actionability + audience_fit + organizer + output_value + deadline + source + quality_bonus + novelty

    if opportunity.quality_status == "rejected":
        total = min(total, 20.0)
    elif opportunity.quality_status == "demoted":
        total = min(total, 44.0)
    elif actionability < 8 and not opportunity.deadline_at:
        total = min(total, 44.0)

    opportunity.relevance_score = round(relevance, 2)
    opportunity.organizer_score = round(organizer + output_value + source, 2)
    opportunity.deadline_score = round(deadline, 2)
    opportunity.novelty_score = round(novelty, 2)
    opportunity.score = round(max(0.0, min(100.0, total)), 2)
    return opportunity
