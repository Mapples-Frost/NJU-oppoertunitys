from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from jinja2 import Environment

from radar.models import Opportunity, RunSummary

TZ = ZoneInfo("Asia/Shanghai")

HTML_TEMPLATE = """
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
  <p class="meta">新增 {{ run.new_items }} 个机会，高优先级 {{ high|length }} 个，截止 7 天内 {{ urgent|length }} 个，抓取失败源 {{ failures|length }} 个。</p>

  {% if high %}
  <h2>一、高优先级</h2>
  {% for item in high %}
    {{ render_item(item)|safe }}
  {% endfor %}
  {% endif %}

  {% if urgent %}
  <h2>二、截止临近</h2>
  {% for item in urgent %}
    {{ render_item(item)|safe }}
  {% endfor %}
  {% endif %}

  {% for category, items in categories.items() %}
  <h2>{{ loop.index + 2 }}、{{ category }}</h2>
  {% for item in items %}
    {{ render_item(item)|safe }}
  {% endfor %}
  {% endfor %}

  <h2>系统状态</h2>
  <p>成功抓取：{{ run.successful_sources }} / {{ run.total_sources }} 个源；总候选：{{ run.total_items }}；入库新增：{{ run.new_items }}。</p>
  {% if run.pack_stats %}
  <h2>源覆盖状态</h2>
  <ul>
  {% for pack, stat in run.pack_stats.items() %}
    <li>{{ pack }}：成功 {{ stat.successful }} / {{ stat.total }}，候选 {{ stat.items }}，新增 {{ stat.new_items }}</li>
  {% endfor %}
  </ul>
  {% endif %}
  {% if failures %}
  <h2>系统异常</h2>
  <ul>
  {% for failure in failures %}
    <li>{{ failure.source_name }}：{{ failure.error }}</li>
  {% endfor %}
  </ul>
  {% endif %}
</body>
</html>
"""

ITEM_TEMPLATE = """
<div class="item">
  <div><span class="score">{{ item.score|round(0, 'floor') }}</span> 分：<strong>{{ item.title }}</strong></div>
  <div><span class="label">类型：</span>{{ item.category }}</div>
  <div><span class="label">截止：</span>{{ deadline_label(item) }}</div>
  <div><span class="label">来源：</span>{{ item.source_name }}</div>
  <div><span class="label">建议：</span>{{ item.recommended_action }}</div>
  {% if item.summary %}<div><span class="label">摘要：</span>{{ item.summary }}</div>{% endif %}
  {% if item.url %}<div><a href="{{ item.url }}">{{ item.url }}</a></div>{% endif %}
</div>
"""


def _days_remaining(item: Opportunity) -> int | None:
    if not item.deadline_at:
        return None
    try:
        deadline = datetime.fromisoformat(item.deadline_at)
    except ValueError:
        return None
    if deadline.tzinfo is None:
        deadline = deadline.replace(tzinfo=TZ)
    return (deadline.astimezone(TZ).date() - datetime.now(TZ).date()).days


def deadline_label(item: Opportunity) -> str:
    days = _days_remaining(item)
    if not item.deadline_at:
        return "未识别，需要人工确认"
    date_text = item.deadline_at[:10]
    confidence = f"，置信度：{item.date_confidence}" if item.date_confidence else ""
    if days is None:
        return f"{date_text}{confidence}"
    if days < 0:
        return f"{date_text}，已过期{confidence}"
    return f"{date_text}，剩余 {days} 天{confidence}"


def _render_item_html(item: Opportunity) -> str:
    env = Environment(autoescape=True)
    env.globals["deadline_label"] = deadline_label
    rendered = env.from_string(ITEM_TEMPLATE).render(item=item)
    return "\n".join(line.rstrip() for line in rendered.splitlines())


def _eligible(items: list[Opportunity], min_score: float) -> list[Opportunity]:
    return sorted([item for item in items if item.score >= min_score], key=lambda item: item.score, reverse=True)


def render_email(
    items: list[Opportunity],
    run: RunSummary,
    failures: list[dict[str, str]],
    email_config: dict[str, Any],
    scoring_config: dict[str, Any],
) -> dict[str, Any]:
    thresholds = scoring_config.get("email_thresholds", {})
    min_score = float(thresholds.get("include", 45))
    high_score = float(thresholds.get("high_priority", 80))
    eligible = _eligible(items, min_score)
    high = [item for item in eligible if item.score >= high_score]
    urgent = [item for item in eligible if (days := _days_remaining(item)) is not None and 0 <= days <= 7]
    used_ids = {item.id for item in high + urgent}
    grouped: dict[str, list[Opportunity]] = defaultdict(list)
    for item in eligible:
        if item.id in used_ids:
            continue
        grouped[item.category or "可选机会"].append(item)
    categories = dict(sorted(grouped.items(), key=lambda pair: pair[0]))
    today = datetime.now(TZ).strftime("%Y-%m-%d")
    title = email_config.get("subject_template", "[NJU Opportunity Radar] {date}: {count} new opportunities").format(
        date=today,
        count=run.new_items,
        high=len(high),
    )

    env = Environment(autoescape=True)
    env.globals["render_item"] = _render_item_html
    env.globals["deadline_label"] = deadline_label
    html = env.from_string(HTML_TEMPLATE).render(
        title=title,
        run=run,
        high=high,
        urgent=urgent,
        categories=categories,
        failures=failures,
    )
    html = "\n".join(line.rstrip() for line in html.splitlines()).strip() + "\n"
    text_lines = [
        title,
        f"新增 {run.new_items} 个机会，高优先级 {len(high)} 个，截止 7 天内 {len(urgent)} 个，失败源 {len(failures)} 个。",
        "",
    ]
    for section, section_items in [("高优先级", high), ("截止临近", urgent), *categories.items()]:
        if not section_items:
            continue
        text_lines.append(section)
        for idx, item in enumerate(section_items, start=1):
            text_lines.append(f"{idx}. {item.title} ({item.score:.0f}分)")
            text_lines.append(f"   类型：{item.category}")
            text_lines.append(f"   截止：{deadline_label(item)}")
            text_lines.append(f"   来源：{item.source_name}")
            text_lines.append(f"   建议：{item.recommended_action}")
            if item.url:
                text_lines.append(f"   链接：{item.url}")
        text_lines.append("")
    if run.pack_stats:
        text_lines.append("源覆盖状态")
        for pack, stat in run.pack_stats.items():
            text_lines.append(
                f"- {pack}: 成功 {stat.get('successful', 0)} / {stat.get('total', 0)}，"
                f"候选 {stat.get('items', 0)}，新增 {stat.get('new_items', 0)}"
            )
        text_lines.append("")
    if failures:
        text_lines.append("系统异常")
        for failure in failures:
            text_lines.append(f"- {failure['source_name']}：{failure['error']}")
    return {"subject": title, "html": html, "text": "\n".join(text_lines).strip() + "\n", "eligible": eligible}
