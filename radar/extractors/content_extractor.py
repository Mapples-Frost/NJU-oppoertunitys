from __future__ import annotations

import logging
from typing import Any

import requests
from bs4 import BeautifulSoup
from requests import RequestException
from requests.exceptions import SSLError

from radar.utils.text import normalize_spaces

LOGGER = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 10
HEADERS = {
    "User-Agent": (
        "NJU-Opportunity-Radar/0.1 "
        "(public pages only; contact: https://github.com/Mapples-Frost/NJU-oppoertunitys)"
    )
}


def fetch_html(url: str, timeout: int = DEFAULT_TIMEOUT) -> str:
    try:
        response = requests.get(url, headers=HEADERS, timeout=timeout)
    except SSLError:
        if url.startswith("https://"):
            response = requests.get("http://" + url.removeprefix("https://"), headers=HEADERS, timeout=timeout)
        else:
            raise
    except RequestException:
        raise
    response.raise_for_status()
    response.encoding = response.apparent_encoding or response.encoding
    return response.text


def extract_content(html: str, url: str | None = None, selector: str | None = None) -> str:
    if not html:
        return ""

    try:
        import trafilatura

        extracted = trafilatura.extract(html, url=url, include_comments=False, include_tables=False)
        if extracted:
            return normalize_spaces(extracted)
    except Exception as exc:  # pragma: no cover - optional library fallback
        LOGGER.debug("trafilatura extraction failed: %s", exc)

    soup = BeautifulSoup(html, "lxml")
    if selector:
        nodes = soup.select(selector)
        text = " ".join(node.get_text(" ", strip=True) for node in nodes)
        if text:
            return normalize_spaces(text)

    candidates = soup.select("article, main, .content, .main, .article, .news-content, #content")
    if candidates:
        text = " ".join(node.get_text(" ", strip=True) for node in candidates)
        if text:
            return normalize_spaces(text)

    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    return normalize_spaces(soup.get_text(" ", strip=True))


def fetch_and_extract(url: str, selector: str | None = None, timeout: int = DEFAULT_TIMEOUT) -> str:
    html = fetch_html(url, timeout=timeout)
    return extract_content(html, url=url, selector=selector)


def get_nested(data: Any, path: str | None, default: Any = None) -> Any:
    if not path:
        return default
    current = data
    for part in path.split("."):
        if isinstance(current, dict):
            current = current.get(part, default)
        elif isinstance(current, list) and part.isdigit():
            index = int(part)
            current = current[index] if 0 <= index < len(current) else default
        else:
            return default
    return current
