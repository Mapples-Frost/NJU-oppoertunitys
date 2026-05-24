from __future__ import annotations

from collections import Counter
from dataclasses import asdict
from typing import Any
from urllib.parse import urlparse

from radar.models import Opportunity

_GENERIC_LIST_PATHS = {
    "/competition",
    "/competitions",
    "/contest",
    "/contests",
    "/challenge",
    "/challenges",
    "/event",
    "/events",
    "/hackathons",
}
_GENERIC_LIST_TITLES = {
    "competition",
    "competitions",
    "contest",
    "contests",
    "challenge",
    "challenges",
    "event",
    "events",
    "hackathons",
}


def _flatten_words(value: Any) -> list[str]:
    if not value:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        words: list[str] = []
        for item in value:
            words.extend(_flatten_words(item))
        return words
    if isinstance(value, dict):
        words = []
        for item in value.values():
            words.extend(_flatten_words(item))
        return words
    return [str(value)]


def _contains_any(text: str, words: list[str]) -> bool:
    lowered = text.lower()
    return any(word and word.lower() in lowered for word in words)


def _matching_words(text: str, words: list[str]) -> list[str]:
    lowered = text.lower()
    return [word for word in words if word and word.lower() in lowered]


def _combined_text(item: Opportunity) -> str:
    return " ".join(
        part
        for part in [
            item.title,
            item.content,
            item.summary,
            item.source_name,
            item.category,
            " ".join(item.tags),
            item.url or "",
        ]
        if part
    )


def _primary_text(item: Opportunity) -> str:
    return " ".join(part for part in [item.title, item.content, item.summary, item.url or ""] if part)


def _is_generic_listing_page(item: Opportunity) -> bool:
    path = urlparse(item.url or "").path.rstrip("/").lower()
    title = " ".join((item.title or "").strip().lower().split())
    return bool(path in _GENERIC_LIST_PATHS and title in _GENERIC_LIST_TITLES)


def _score_actionability(item: Opportunity, text: str, quality: dict[str, Any]) -> tuple[float, list[str]]:
    action_terms = _flatten_words(quality.get("action_terms"))
    strong_terms = _flatten_words(quality.get("strong_action_terms"))
    matches = _matching_words(text, action_terms)
    strong_matches = _matching_words(text, strong_terms)
    score = min(20.0, len(matches) * 4.0) + min(16.0, len(strong_matches) * 8.0)
    notes = [f"action:{word}" for word in matches[:4]]
    notes.extend(f"strong_action:{word}" for word in strong_matches[:3])
    if item.deadline_at:
        score += 10.0
        notes.append("deadline_detected")
    if item.source_pack == "competition_pack" and _contains_any(text, ["competition", "competitions", "challenge", "竞赛", "大赛", "赛题"]):
        score += 12.0
        notes.append("competition_source")
    if item.source_pack == "research_pack" and _contains_any(text, ["cfp", "call for papers", "投稿", "征稿", "workshop"]):
        score += 14.0
        notes.append("research_cfp")
    return min(40.0, score), notes


def _score_audience(item: Opportunity, text: str, profile: dict[str, Any]) -> tuple[float, list[str]]:
    interests = _flatten_words(profile.get("interests"))
    audience = _flatten_words(profile.get("audience"))
    preferred_categories = _flatten_words(profile.get("preferred_categories"))
    interest_matches = _matching_words(text, interests)
    audience_matches = _matching_words(text, audience)
    category_matches = _matching_words(item.category or "", preferred_categories)
    score = min(18.0, len(interest_matches) * 4.0) + min(12.0, len(audience_matches) * 4.0)
    if category_matches:
        score += 8.0
    if item.source_pack == "nju_pack":
        score += 10.0
    notes = [f"interest:{word}" for word in interest_matches[:4]]
    notes.extend(f"audience:{word}" for word in audience_matches[:3])
    if category_matches:
        notes.append("preferred_category")
    return min(35.0, score), notes


def _feedback_adjustment(item: Opportunity, text: str, feedback: dict[str, Any]) -> tuple[float, list[str]]:
    notes: list[str] = []
    boost = _flatten_words(feedback.get("boost"))
    prefer_sources = set(_flatten_words(feedback.get("prefer_sources")))
    adjustment = 0.0
    matches = _matching_words(text, boost)
    if matches:
        adjustment += min(16.0, len(matches) * 8.0)
        notes.extend(f"user_boost:{word}" for word in matches[:3])
    if item.source_id in prefer_sources or item.source_name in prefer_sources:
        adjustment += 8.0
        notes.append("preferred_source")
    return adjustment, notes


def evaluate_quality(
    item: Opportunity,
    profile: dict[str, Any],
    quality: dict[str, Any],
    feedback: dict[str, Any],
) -> Opportunity:
    text = _combined_text(item)
    primary_text = _primary_text(item)
    lowered_url = (item.url or "").lower()
    gate = quality.get("quality_gate", {})
    notes: list[str] = []

    muted_sources = set(_flatten_words(feedback.get("mute_sources")))
    if item.source_id in muted_sources or item.source_name in muted_sources:
        return _reject(item, "muted_source", ["source muted by feedback"])

    user_reject = _matching_words(text, _flatten_words(feedback.get("reject")))
    if user_reject:
        return _reject(item, "user_reject", [f"user_reject:{user_reject[0]}"])

    hard_matches = _matching_words(text, _flatten_words(quality.get("hard_reject_terms")))
    reject_url_parts = _flatten_words(quality.get("reject_url_parts"))
    if hard_matches:
        return _reject(item, "hard_reject_term", [f"hard_reject:{hard_matches[0]}"])
    if any(part.lower() in lowered_url for part in reject_url_parts):
        return _reject(item, "hard_reject_url", ["hard_reject_url"])
    if _is_generic_listing_page(item):
        return _reject(item, "generic_listing_page", ["generic listing page"])

    actionability, action_notes = _score_actionability(item, primary_text, quality)
    audience_fit, audience_notes = _score_audience(item, text, profile)
    feedback_bonus, feedback_notes = _feedback_adjustment(item, text, feedback)
    notes.extend(action_notes)
    notes.extend(audience_notes)
    notes.extend(feedback_notes)

    product_matches = _matching_words(primary_text, _flatten_words(quality.get("product_terms")))
    if product_matches and actionability < float(gate.get("actionability_min", 12)):
        return _reject(item, "product_or_marketing_page", [f"product:{product_matches[0]}"])

    profile_exclude = _matching_words(text, _flatten_words(profile.get("exclude")))
    if profile_exclude and actionability < float(gate.get("actionability_min", 12)):
        return _reject(item, "profile_exclude", [f"profile_exclude:{profile_exclude[0]}"])

    source_bonus = 10.0
    source_quality = quality.get("quality_sources", {})
    if item.source_id in set(_flatten_words(source_quality.get("prefer"))):
        source_bonus += 8.0
        notes.append("source_preferred")
    if item.source_id in set(_flatten_words(source_quality.get("demote"))):
        source_bonus -= 8.0
        notes.append("source_demoted")

    demote_matches = _matching_words(text, _flatten_words(quality.get("demote_terms")))
    demote_penalty = min(12.0, len(demote_matches) * 4.0)
    if demote_matches:
        notes.append(f"demote:{demote_matches[0]}")

    background_matches = _matching_words(text, _flatten_words(quality.get("background_terms")))
    background_bonus = min(4.0, len(background_matches) * 1.0)
    quality_score = max(0.0, actionability + audience_fit + source_bonus + feedback_bonus + background_bonus - demote_penalty)

    item.actionability_score = round(actionability, 2)
    item.audience_fit_score = round(audience_fit, 2)
    item.quality_score = round(quality_score, 2)
    item.quality_notes = "; ".join(notes[:12])
    item.reject_reason = ""

    min_quality = float(gate.get("min_quality_score", 45))
    demote_below = float(gate.get("demote_below", 58))
    min_action = float(gate.get("actionability_min", 12))
    min_audience = float(gate.get("audience_fit_min", 6))

    if actionability < min_action and audience_fit < min_audience:
        item.quality_status = "rejected"
        item.reject_reason = "not_actionable_or_not_relevant"
    elif quality_score < min_quality:
        item.quality_status = "rejected"
        item.reject_reason = "quality_score_below_threshold"
    elif quality_score < demote_below:
        item.quality_status = "demoted"
        item.reject_reason = "low_quality_confidence"
    else:
        item.quality_status = "accepted"
    return item


def _reject(item: Opportunity, reason: str, notes: list[str]) -> Opportunity:
    item.quality_status = "rejected"
    item.reject_reason = reason
    item.quality_score = 0.0
    item.quality_notes = "; ".join(notes)
    item.actionability_score = item.actionability_score or 0.0
    item.audience_fit_score = item.audience_fit_score or 0.0
    return item


def item_quality_record(item: Opportunity) -> dict[str, Any]:
    row = asdict(item)
    return {
        key: row.get(key)
        for key in [
            "id",
            "title",
            "url",
            "source_id",
            "source_name",
            "source_pack",
            "category",
            "score",
            "quality_status",
            "quality_score",
            "actionability_score",
            "audience_fit_score",
            "reject_reason",
            "quality_notes",
        ]
    }


def build_quality_report(items: list[Opportunity], failures: list[dict[str, str]]) -> dict[str, Any]:
    status_counts = Counter(item.quality_status or "accepted" for item in items)
    reason_counts = Counter(item.reject_reason for item in items if item.reject_reason)
    by_source: dict[str, dict[str, Any]] = {}
    for item in items:
        source_id = item.source_id or "unknown"
        row = by_source.setdefault(
            source_id,
            {
                "source_name": item.source_name,
                "source_pack": item.source_pack,
                "candidates": 0,
                "accepted": 0,
                "demoted": 0,
                "rejected": 0,
                "reject_reasons": Counter(),
            },
        )
        row["candidates"] += 1
        status = item.quality_status or "accepted"
        row[status] = row.get(status, 0) + 1
        if item.reject_reason:
            row["reject_reasons"][item.reject_reason] += 1
    source_quality = []
    for source_id, row in by_source.items():
        reasons = row.pop("reject_reasons")
        row["source_id"] = source_id
        row["reject_reasons"] = dict(reasons.most_common(5))
        source_quality.append(row)
    source_quality.sort(key=lambda row: (-row.get("rejected", 0), row["source_id"]))

    return {
        "total_items": len(items),
        "accepted": status_counts.get("accepted", 0),
        "demoted": status_counts.get("demoted", 0),
        "rejected": status_counts.get("rejected", 0),
        "reject_reasons": dict(reason_counts.most_common()),
        "failed_sources": len(failures),
        "source_quality": source_quality,
        "top_accepted": [item_quality_record(item) for item in sorted(
            [item for item in items if item.quality_status == "accepted"],
            key=lambda item: (item.quality_score, item.score),
            reverse=True,
        )[:20]],
    }


def source_quality_report(quality_report: dict[str, Any]) -> list[dict[str, Any]]:
    return list(quality_report.get("source_quality", []))
