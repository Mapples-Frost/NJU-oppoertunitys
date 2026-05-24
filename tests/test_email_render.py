from radar.mailer.render_email import render_email
from radar.models import Opportunity, RunSummary


def test_render_email_shows_top_items_and_hides_failure_details():
    run = RunSummary(id="1", started_at="2026-05-24T08:00:00+08:00", new_items=2, total_sources=2, successful_sources=1)
    run.pack_stats = {"competition_pack": {"total": 2, "successful": 1, "failed": 1, "items": 2, "new_items": 2}}
    good = Opportunity(
        id="x",
        title="华为软件精英挑战赛报名开启",
        url="https://example.com",
        source_id="huawei",
        source_name="华为",
        source_group="enterprise",
        category="企业开发者赛事",
        score=91,
        quality_status="accepted",
        quality_score=90,
        summary="AI 算法赛事。",
    )
    rejected = Opportunity(
        id="bad",
        title="百炼大模型",
        url="https://example.com/model",
        source_id="aliyun",
        source_name="阿里云",
        source_group="enterprise",
        category="企业开发者赛事",
        score=64,
        quality_status="rejected",
        reject_reason="product_or_marketing_page",
    )

    rendered = render_email(
        [good, rejected],
        run,
        [{"source_id": "bad", "source_name": "坏源", "error": "HTTP 403"}],
        {"subject_template": "[NJU Opportunity Radar] {date}: {count}"},
        {"email_thresholds": {"include": 45, "high_priority": 80}},
        {"email": {"top_limit": 15, "include_demoted": False}},
    )

    assert "华为软件精英挑战赛报名开启" in rendered["text"]
    assert "百炼大模型" not in rendered["text"]
    assert "完整列表见 logs/latest_run.json" in rendered["text"]
    assert "HTTP 403" not in rendered["html"]
    assert len(rendered["eligible"]) == 1


def test_render_email_caps_top_items_at_15():
    run = RunSummary(id="1", started_at="2026-05-24T08:00:00+08:00", new_items=20)
    items = [
        Opportunity(
            id=str(idx),
            title=f"AI 算法挑战赛 {idx}",
            url=f"https://example.com/{idx}",
            source_id="s",
            source_name="S",
            source_group="competition",
            category="AI / 算法竞赛",
            score=90 - idx,
            quality_status="accepted",
            quality_score=90 - idx,
        )
        for idx in range(20)
    ]

    rendered = render_email(
        items,
        run,
        [],
        {"subject_template": "[NJU Opportunity Radar] {date}: {count}"},
        {"email_thresholds": {"include": 45, "high_priority": 80}},
        {"email": {"top_limit": 15, "include_demoted": False}},
    )

    assert len(rendered["eligible"]) == 15
