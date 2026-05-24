from __future__ import annotations

from rapidfuzz import fuzz

from radar.models import Opportunity
from radar.utils.hash import stable_hash
from radar.utils.text import clean_title
from radar.utils.url import canonicalize_url


def enrich_identity(opportunity: Opportunity) -> Opportunity:
    canonical_url = canonicalize_url(opportunity.url)
    opportunity.url = canonical_url or opportunity.url
    title_key = clean_title(opportunity.title)
    opportunity.title_hash = stable_hash(title_key) if title_key else ""
    opportunity.url_hash = stable_hash(canonical_url) if canonical_url else ""
    opportunity.content_hash = stable_hash(opportunity.content) if opportunity.content else ""
    if canonical_url:
        opportunity.id = stable_hash(f"url:{canonical_url}")
    else:
        opportunity.id = stable_hash(
            f"title:{title_key}|source:{opportunity.source_id}|published:{opportunity.published_at or ''}"
        )
    return opportunity


def _is_better(candidate: Opportunity, current: Opportunity) -> bool:
    candidate_score = (
        int(bool(candidate.deadline_at)) * 20
        + min(len(candidate.content), 2000) / 100
        + candidate.score
        + len(candidate.tags)
    )
    current_score = (
        int(bool(current.deadline_at)) * 20
        + min(len(current.content), 2000) / 100
        + current.score
        + len(current.tags)
    )
    return candidate_score > current_score


def _merge(target: Opportunity, incoming: Opportunity) -> Opportunity:
    if _is_better(incoming, target):
        incoming.discovered_at = target.discovered_at
        incoming.id = target.id
        target = incoming
    merged_tags = list(dict.fromkeys([*target.tags, *incoming.tags]))
    target.tags = merged_tags
    if incoming.source_name not in target.source_name:
        target.source_name = f"{target.source_name}; {incoming.source_name}"
    return target


def merge_duplicates(items: list[Opportunity], similarity_threshold: int = 88) -> list[Opportunity]:
    merged: list[Opportunity] = []
    by_key: dict[str, int] = {}
    for item in items:
        item = enrich_identity(item)
        keys = [key for key in [item.url_hash, item.title_hash] if key]
        match_index = None
        for key in keys:
            if key in by_key:
                match_index = by_key[key]
                break
        if match_index is None:
            cleaned = clean_title(item.title)
            for idx, existing in enumerate(merged):
                existing_cleaned = clean_title(existing.title)
                if cleaned and existing_cleaned and fuzz.token_set_ratio(cleaned, existing_cleaned) >= similarity_threshold:
                    match_index = idx
                    break
        if match_index is None:
            by_key.update({key: len(merged) for key in keys})
            merged.append(item)
        else:
            merged[match_index] = _merge(merged[match_index], item)
            for key in keys:
                by_key[key] = match_index
    return merged
