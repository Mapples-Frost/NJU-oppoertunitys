from __future__ import annotations

import re
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from bs4 import BeautifulSoup

from radar.utils.text import normalize_spaces

WECHAT_URL_RE = re.compile(r"https?://mp\.weixin\.qq\.com/[^\s<>'\"）)]+")
KEEP_QUERY_KEYS = {"__biz", "mid", "idx", "sn", "chksm", "scene"}


def extract_wechat_urls(text: str | None) -> list[str]:
    if not text:
        return []
    urls = []
    for match in WECHAT_URL_RE.finditer(text):
        url = normalize_wechat_url(match.group(0))
        if url and url not in urls:
            urls.append(url)
    return urls


def normalize_wechat_url(url: str | None) -> str:
    if not url:
        return ""
    value = url.strip().rstrip("，。；;、")
    parsed = urlparse(value)
    if parsed.netloc.lower() != "mp.weixin.qq.com":
        return ""
    query = [(key, val) for key, val in parse_qsl(parsed.query, keep_blank_values=False) if key in KEEP_QUERY_KEYS]
    path = parsed.path.rstrip("/") or "/"
    return urlunparse(("https", "mp.weixin.qq.com", path, "", urlencode(query), ""))


def parse_wechat_article_html(html: str, url: str) -> dict[str, str]:
    soup = BeautifulSoup(html, "lxml")
    title = _first_text(soup, ["#activity-name", "h1.rich_media_title", "h1"])
    account = _first_text(soup, ["#js_name", ".rich_media_meta_text", ".profile_meta_value"])
    publish_time = _first_text(soup, ["#publish_time", "em#publish_time"])
    author = _first_text(soup, ["#js_author_name", ".rich_media_meta.rich_media_meta_text"])
    content_node = soup.select_one("#js_content, .rich_media_content, article")
    content = normalize_spaces(content_node.get_text(" ", strip=True) if content_node else soup.get_text(" ", strip=True))
    description = ""
    meta = soup.select_one('meta[property="og:description"], meta[name="description"]')
    if meta and meta.get("content"):
        description = normalize_spaces(str(meta.get("content")))
    return {
        "title": title or description[:60] or "微信公众号文章",
        "account": account,
        "author": author,
        "published_at": publish_time,
        "content": content,
        "summary": description,
        "url": normalize_wechat_url(url) or url,
    }


def _first_text(soup: BeautifulSoup, selectors: list[str]) -> str:
    for selector in selectors:
        node = soup.select_one(selector)
        if node:
            text = normalize_spaces(node.get_text(" ", strip=True))
            if text:
                return text
    return ""
