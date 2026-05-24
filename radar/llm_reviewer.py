from __future__ import annotations

import json
import logging
import os
from typing import Any

import requests

from radar.models import Opportunity

LOGGER = logging.getLogger(__name__)


def _enabled() -> tuple[str, str, str] | None:
    api_key = os.getenv("LLM_API_KEY", "").strip()
    model = os.getenv("LLM_MODEL", "").strip()
    if not api_key or not model:
        return None
    base_url = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1/chat/completions").strip()
    return api_key, model, base_url


def review_candidates(items: list[Opportunity], limit: int = 30) -> list[Opportunity]:
    settings = _enabled()
    if not settings:
        return items
    api_key, model, base_url = settings
    candidates = [item for item in items if item.quality_status in {"accepted", "demoted"}][:limit]
    if not candidates:
        return items
    try:
        decisions = _call_llm(candidates, api_key, model, base_url)
    except Exception as exc:  # pragma: no cover - network fallback
        LOGGER.warning("LLM review failed, using rule results: %s", exc)
        return items
    by_id = {item.id: item for item in items}
    for decision in decisions:
        item_id = str(decision.get("id", ""))
        item = by_id.get(item_id)
        if not item:
            continue
        confidence = _safe_float(decision.get("confidence"), 0.0)
        item.llm_confidence = confidence
        summary = str(decision.get("summary") or "").strip()
        if summary:
            item.llm_summary = summary
            item.summary = summary
        next_action = str(decision.get("next_action") or "").strip()
        if next_action:
            item.recommended_action = next_action
        if decision.get("is_actionable") is False and confidence >= 0.7:
            item.quality_status = "rejected"
            item.reject_reason = "llm_not_actionable"
            item.quality_notes = f"{item.quality_notes}; llm:not_actionable".strip("; ")
            item.score = min(item.score, 20.0)
        elif decision.get("audience_fit") is False and confidence >= 0.7:
            item.quality_status = "demoted"
            item.reject_reason = "llm_low_audience_fit"
            item.score = min(item.score, 44.0)
    return items


def _call_llm(candidates: list[Opportunity], api_key: str, model: str, base_url: str) -> list[dict[str, Any]]:
    payload_items = [
        {
            "id": item.id,
            "title": item.title,
            "source": item.source_name,
            "category": item.category,
            "url": item.url,
            "summary": item.summary or item.content[:500],
            "score": item.score,
            "quality_notes": item.quality_notes,
        }
        for item in candidates
    ]
    prompt = (
        "You review opportunity radar candidates for a Nanjing University student. "
        "Return JSON only: an array of objects with id, is_actionable, audience_fit, "
        "summary, why_relevant, next_action, confidence. Reject product pages, navigation pages, "
        "organization introductions, proceedings pages, and pages without a clear action."
    )
    response = requests.post(
        base_url,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "model": model,
            "messages": [
                {"role": "system", "content": prompt},
                {"role": "user", "content": json.dumps(payload_items, ensure_ascii=False)},
            ],
            "temperature": 0,
        },
        timeout=45,
    )
    response.raise_for_status()
    data = response.json()
    content = data["choices"][0]["message"]["content"]
    parsed = json.loads(_strip_code_fence(content))
    return parsed if isinstance(parsed, list) else []


def _strip_code_fence(value: str) -> str:
    text = value.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return text


def _safe_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default
