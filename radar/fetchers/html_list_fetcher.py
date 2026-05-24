from __future__ import annotations

from typing import Any

from bs4 import BeautifulSoup

from radar.extractors.content_extractor import DEFAULT_TIMEOUT, fetch_and_extract, fetch_html
from radar.models import Opportunity, SourceResult
from radar.utils.text import normalize_spaces
from radar.utils.url import canonicalize_url

IGNORE_TITLE_PARTS = [
    "登录",
    "注册",
    "合作伙伴",
    "社区论坛",
    "关于大赛",
    "更多赛事",
    "天池学习",
    "联系我们",
    "关于我们",
    "体验中心",
    "案例广场",
    "隐私",
    "条款",
    "公网安备",
    "ICP备",
    "copyright",
    "首页",
    "skip to main content",
    "main content",
    "about",
    "关于caai",
    "caai简介",
    "证书下载",
    "证书验证",
    "竞赛获奖证书下载",
    "志愿者证书下载",
    "人才项目库",
    "竞赛组织",
]
IGNORE_URL_PARTS = [
    "/login",
    "/auth/",
    "beian.gov.cn",
    "privacy",
    "terms",
    "register",
    "copyright",
]


def _select_text(node: Any, selector: str | None) -> str:
    if selector:
        selected = node.select_one(selector)
        if selected:
            return normalize_spaces(selected.get_text(" ", strip=True))
    return normalize_spaces(node.get_text(" ", strip=True))


def _select_link(node: Any, selector: str | None) -> str | None:
    selected = node.select_one(selector) if selector else None
    target = selected or node
    return target.get("href") if hasattr(target, "get") else None


def _looks_like_navigation(title: str, url: str) -> bool:
    lower_url = url.lower()
    lower_title = title.lower()
    if any(part.lower() in lower_title for part in IGNORE_TITLE_PARTS):
        return True
    if any(part.lower() in lower_url for part in IGNORE_URL_PARTS):
        return True
    return False


def fetch_html_list(source: dict[str, Any]) -> SourceResult:
    source_id = source["id"]
    source_name = source["name"]
    result = SourceResult(source_id=source_id, source_name=source_name, source_type="html_list")
    try:
        list_url = source["list_url"]
        html = fetch_html(list_url, timeout=int(source.get("timeout", DEFAULT_TIMEOUT)))
        soup = BeautifulSoup(html, "lxml")
        nodes = soup.select(source.get("list_selector", "a"))
        max_items = int(source.get("max_items", 8))
        seen: set[str] = set()
        for node in nodes:
            title = _select_text(node, source.get("title_selector"))
            link = _select_link(node, source.get("link_selector"))
            url = canonicalize_url(link, source.get("base_url") or list_url)
            if not title or not url or url in seen:
                continue
            if _looks_like_navigation(title, url):
                continue
            if len(title) < int(source.get("min_title_length", 4)):
                continue
            seen.add(url)
            date_text = _select_text(node, source.get("date_selector")) if source.get("date_selector") else None
            content = ""
            if source.get("detail_required", True):
                try:
                    content = fetch_and_extract(
                        url,
                        selector=source.get("detail_content_selector"),
                        timeout=int(source.get("timeout", DEFAULT_TIMEOUT)),
                    )
                except Exception as exc:
                    content = f"{title} {date_text or ''}".strip()
                    result.items.append(
                        Opportunity(
                            title=title,
                            url=url,
                            source_id=source_id,
                            source_name=source_name,
                            source_group=source.get("group", ""),
                            published_at=date_text,
                            content=content,
                            category=source.get("category_hint", ""),
                            tags=list(source.get("tags", [])),
                            raw={"source_weight": source.get("weight", 1.0), "detail_error": str(exc)},
                        )
                    )
                    if len(result.items) >= max_items:
                        break
                    continue
            result.items.append(
                Opportunity(
                    title=title,
                    url=url,
                    source_id=source_id,
                    source_name=source_name,
                    source_group=source.get("group", ""),
                    published_at=date_text,
                    content=content,
                    category=source.get("category_hint", ""),
                    tags=list(source.get("tags", [])),
                    raw={"source_weight": source.get("weight", 1.0)},
                )
            )
            if len(result.items) >= max_items:
                break
    except Exception as exc:
        result.error = str(exc)
    if not result.items and result.error is None:
        result.error = "no list items matched"
    return result
