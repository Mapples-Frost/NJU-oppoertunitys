from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a YAML mapping")
    return data


def load_config(config_dir: Path) -> dict[str, Any]:
    config_dir = config_dir.resolve()
    return {
        "config_dir": config_dir,
        "sources": load_yaml(config_dir / "sources.yml"),
        "keywords": load_yaml(config_dir / "keywords.yml"),
        "scoring": load_yaml(config_dir / "scoring.yml"),
        "email": load_yaml(config_dir / "email.yml"),
    }


def enabled_sources(config: dict[str, Any]) -> list[dict[str, Any]]:
    sources = config.get("sources", {}).get("sources", [])
    if not isinstance(sources, list):
        raise ValueError("config/sources.yml must define a sources list")
    enabled = [normalize_source(source) for source in sources if source.get("enabled", True)]
    ids = [source.get("id") for source in enabled]
    if len(ids) != len(set(ids)):
        raise ValueError("enabled source ids must be unique")
    return enabled


def normalize_source(source: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(source)
    source_type = normalized.get("type", "")
    group = normalized.get("group", "")
    if not normalized.get("source_pack"):
        normalized["source_pack"] = default_source_pack(source_type, group)
    if not normalized.get("domain"):
        normalized["domain"] = default_domain(source_type, group)
    if not normalized.get("source_tier"):
        normalized["source_tier"] = "core" if group in {"nju", "competition", "academic"} else "extended"
    return normalized


def default_source_pack(source_type: str, group: str) -> str:
    if source_type in {"wechat_article", "imap_email", "webhook_inbox"}:
        return "wechat_pack"
    if group == "competition":
        return "competition_pack"
    if group == "academic":
        return "research_pack"
    if group == "nju":
        return "nju_pack"
    if group == "enterprise":
        return "competition_pack"
    if group == "manual":
        return "wechat_pack"
    return "extended_pack"


def default_domain(source_type: str, group: str) -> str:
    if source_type in {"wechat_article", "imap_email", "webhook_inbox"}:
        return "wechat"
    if group == "competition":
        return "competition"
    if group == "academic":
        return "research"
    if group == "nju":
        return "nju"
    if group == "enterprise":
        return "enterprise"
    if group == "manual":
        return "wechat"
    return group or source_type or "unknown"
