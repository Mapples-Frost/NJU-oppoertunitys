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
    enabled = [source for source in sources if source.get("enabled", True)]
    ids = [source.get("id") for source in enabled]
    if len(ids) != len(set(ids)):
        raise ValueError("enabled source ids must be unique")
    return enabled
