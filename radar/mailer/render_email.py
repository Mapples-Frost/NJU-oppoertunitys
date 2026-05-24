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
    .muted { color: #667085; }
    a { color: #175cd3; }
  </style>
</head>
<body>
  <h1>{{ title }}</h1>
  <p class="meta">新增 {{ run.new_items }} 个机会，主邮件展示 {{ top_items|length }} 个，截止 7 天内 {{ urgent|length }} 个，失败源 {{ failures|length }} 个。</p>

  {% if top_items %}
  <h2>最值得看</h2>
  {% for item in top_items %}
    {{ render_item(item)|safe }}
  {% endfor %}
  {% else %}
  <p class="muted">今天没有通过质量门的高价值机会。系统仍已完成抓取，详情见日志。</p>
  {% endif %}

  {% if urgent %}
  <h2>截止临近</h2>
  {% for item in urgent %}
    {{ render_item(item)|safe }}
  {% endfor %}
  {% endif %}

  {% for category, items in categories.items() %}
  <h2>{{ category }}</h2>
  {% for item in items %}
    {{ render_item(item)|safe }}
  {% endfor %}
  {% endfor %}

  <h2>源覆盖状态</h2>
  <p>成功抓取：{{ run.successful_sources }} / {{ run.total_sources }} 个源；总候选：{{ run.total_items }}；入库新增：{{ run.new_items }}。</p>
  {% if run.pack_stats %}
  <ul>
  {% for pack, stat in run.pack_stats.items() %}
    <li>{{ pack }}：成功 {{ stat.successful }} / {{ stat.total }}，候选 {{ stat.items }}，新增 {{ stat.new_items }}</li>
  {% endfor %}
  </ul>
  {% endif %}
  {% if failures %}
  <p class="muted">本次有 {{ failures|length }} 个源异常，完整列表已写入 logs/latest_run.json，避免在邮件正文刷屏。</p>
  {% endif %}
  <p class="muted">质量报告：logs/latest_quality_report.json；被过滤条目：logs/latest_rejected_items.json。</p>
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
  {% if item.llm_summary or item.summary %}<div><span class="label">摘要：</span>{{ item.llm_summary or item.summary }}</div>{% endif %}
  {% if item.quality_notes %}<div><span class="label">质量依据：</span>{{ item.quality_notes }}</div>{% endif %}
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


def _eligible(items: list[Opportunity], min_score: float, include_demoted: bool) -> list[Opportunity]:
    allowed_statuses = {"accepted", "demoted"} if include_demoted else {"accepted"}
    return sorted(
        [
            item
            for item in items
            if item.score >= min_score and (item.quality_status or "accepted") in allowed_statuses
        ],
        key=lambda item: (item.quality_score, item.score),
        reverse=True,
    )


def render_email(
    items: list[Opportunity],
    run: RunSummary,
    failures: list[dict[str, str]],
    email_config: dict[str, Any],
    scoring_config: dict[str, Any],
    quality_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    thresholds = scoring_config.get("email_thresholds", {})
    min_score = float(thresholds.get("include", 45))
    quality_email = (quality_config or {}).get("email", {})
    top_limit = int(quality_email.get("top_limit", 15))
    include_demoted = bool(quality_email.get("include_demoted", False))
    eligible = _eligible(items, min_score, include_demoted)
    top_items = eligible[:top_limit]
    used_ids = {item.id for item in top_items}
    urgent = [
        item
        for item in eligible
        if item.id not in used_ids and (days := _days_remaining(item)) is not None and 0 <= days <= 7
    ][:5]
    used_ids.update(item.id for item in urgent)
    grouped: dict[str, list[Opportunity]] = defaultdict(list)
    for item in eligible:
        if item.id in used_ids:
            continue
        grouped[item.category or "可选机会"].append(item)
    categories = {
        category: category_items[:5]
        for category, category_items in sorted(grouped.items(), key=lambda pair: pair[0])
        if category_items
    }
    today = datetime.now(TZ).strftime("%Y-%m-%d")
    title = email_config.get("subject_template", "[NJU Opportunity Radar] {date}: {count} new opportunities").format(
        date=today,
        count=run.new_items,
        high=len(top_items),
    )

    env = Environment(autoescape=True)
    env.globals["render_item"] = _render_item_html
    env.globals["deadline_label"] = deadline_label
    html = env.from_string(HTML_TEMPLATE).render(
        title=title,
        run=run,
        top_items=top_items,
        urgent=urgent,
        categories=categories,
        failures=failures,
    )
    html = "\n".join(line.rstrip() for line in html.splitlines()).strip() + "\n"
    text_lines = [
        title,
        f"新增 {run.new_items} 个机会，主邮件展示 {len(top_items)} 个，截止 7 天内 {len(urgent)} 个，失败源 {len(failures)} 个。",
        "",
    ]
    if top_items:
        text_lines.append("最值得看")
        _append_items(text_lines, top_items)
    else:
        text_lines.append("今天没有通过质量门的高价值机会。")
        text_lines.append("")
    if urgent:
        text_lines.append("截止临近")
        _append_items(text_lines, urgent)
    for section, section_items in categories.items():
        text_lines.append(section)
        _append_items(text_lines, section_items)
    text_lines.append("源覆盖状态")
    for pack, stat in run.pack_stats.items():
        text_lines.append(f"- {pack}: 成功 {stat.get('successful', 0)} / {stat.get('total', 0)}，候选 {stat.get('items', 0)}，新增 {stat.get('new_items', 0)}")
    if failures:
        text_lines.append(f"- 系统异常 {len(failures)} 个，完整列表见 logs/latest_run.json")
    text_lines.append("- 质量报告见 logs/latest_quality_report.json")
    return {"subject": title, "html": html, "text": "\n".join(text_lines).strip() + "\n", "eligible": top_items}


def _append_items(text_lines: list[str], items: list[Opportunity]) -> None:
    for idx, item in enumerate(items, start=1):
        text_lines.append(f"{idx}. {item.title} ({item.score:.0f}分，质量 {item.quality_score:.0f})")
        text_lines.append(f"   类型：{item.category}")
        text_lines.append(f"   截止：{deadline_label(item)}")
        text_lines.append(f"   来源：{item.source_name}")
        text_lines.append(f"   建议：{item.recommended_action}")
        if item.llm_summary or item.summary:
            text_lines.append(f"   摘要：{item.llm_summary or item.summary}")
        if item.url:
            text_lines.append(f"   链接：{item.url}")
    text_lines.append("")
