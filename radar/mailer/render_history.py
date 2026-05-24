from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from jinja2 import Environment

from radar.mailer.render_email import _render_item_html, deadline_label
from radar.models import Opportunity

TZ = ZoneInfo("Asia/Shanghai")

HISTORY_HTML_TEMPLATE = """
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; color: #172033; line-height: 1.55; }
    h1 { font-size: 22px; margin-bottom: 8px; }
    h2 { font-size: 17px; margin-top: 28px; border-bottom: 1px solid #d8dee9; padding-bottom: 6px; }
    .meta { color: #667085; }
    .item { margin: 16px 0; padding: 12px 14px; border: 1px solid #d8dee9; border-radius: 8px; }
    .score { font-weight: 700; color: #b42318; }
    .label { color: #475467; }
    a { color: #175cd3; }
  </style>
</head>
<body>
  <h1>{{ title }}</h1>
  <p class="meta">数据库当前共 {{ total }} 条机会，本邮件展示 {{ shown }} 条，生成时间 {{ generated_at }}。</p>

  <h2>来源包概览</h2>
  <ul>
  {% for pack, count in pack_counts.items() %}
    <li>{{ pack }}：{{ count }} 条</li>
  {% endfor %}
  </ul>

  <h2>分类概览</h2>
  <ul>
  {% for category, count in category_counts.items() %}
    <li>{{ category }}：{{ count }} 条</li>
  {% endfor %}
  </ul>

  {% for category, category_items in categories.items() %}
  <h2>{{ category }}（{{ category_items|length }}）</h2>
  {% for item in category_items %}
    {{ render_item(item)|safe }}
  {% endfor %}
  {% endfor %}
</body>
</html>
"""


def _sort_key(item: Opportunity) -> tuple[float, str, str]:
    deadline = item.deadline_at or "9999-12-31"
    discovered = item.discovered_at or ""
    return (-item.score, deadline, discovered)


def render_history_email(
    items: list[Opportunity],
    email_config: dict[str, Any],
    total_count: int | None = None,
) -> dict[str, Any]:
    sorted_items = sorted(items, key=_sort_key)
    total = total_count if total_count is not None else len(sorted_items)
    generated_at = datetime.now(TZ).strftime("%Y-%m-%d %H:%M")
    title = f"[NJU Opportunity Radar] 历史机会汇总：{len(sorted_items)} / {total} 条"

    categories: dict[str, list[Opportunity]] = defaultdict(list)
    for item in sorted_items:
        categories[item.category or "未分类"].append(item)
    categories = dict(sorted(categories.items(), key=lambda pair: (-len(pair[1]), pair[0])))
    category_counts = dict((category, len(category_items)) for category, category_items in categories.items())
    pack_counts = dict(Counter(item.source_pack or "unknown_pack" for item in sorted_items).most_common())

    env = Environment(autoescape=True)
    env.globals["render_item"] = _render_item_html
    env.globals["deadline_label"] = deadline_label
    html = env.from_string(HISTORY_HTML_TEMPLATE).render(
        title=title,
        total=total,
        shown=len(sorted_items),
        generated_at=generated_at,
        categories=categories,
        category_counts=category_counts,
        pack_counts=pack_counts,
    )
    html = "\n".join(line.rstrip() for line in html.splitlines()).strip() + "\n"

    text_lines = [
        title,
        f"数据库当前共 {total} 条机会，本邮件展示 {len(sorted_items)} 条，生成时间 {generated_at}。",
        "",
        "来源包概览",
    ]
    for pack, count in pack_counts.items():
        text_lines.append(f"- {pack}: {count} 条")
    text_lines.extend(["", "分类概览"])
    for category, count in category_counts.items():
        text_lines.append(f"- {category}: {count} 条")
    text_lines.append("")

    for category, category_items in categories.items():
        text_lines.append(f"{category}（{len(category_items)}）")
        for idx, item in enumerate(category_items, start=1):
            text_lines.append(f"{idx}. {item.title} ({item.score:.0f}分)")
            text_lines.append(f"   截止：{deadline_label(item)}")
            text_lines.append(f"   来源：{item.source_name}")
            if item.url:
                text_lines.append(f"   链接：{item.url}")
        text_lines.append("")

    return {
        "subject": title,
        "html": "\n".join(line.rstrip() for line in html.splitlines()).strip() + "\n",
        "text": "\n".join(text_lines).strip() + "\n",
        "eligible": sorted_items,
    }
