from radar.mailer.render_history import render_history_email
from radar.models import Opportunity


def test_render_history_email_includes_all_items_and_quality_status():
    items = [
        Opportunity(
            id="low",
            title="低分历史机会也要发送",
            url="https://example.com/low",
            source_id="manual",
            source_name="Manual",
            source_group="manual",
            source_pack="wechat_pack",
            category="其他",
            score=12,
            quality_status="rejected",
            reject_reason="not_actionable",
        ),
        Opportunity(
            id="high",
            title="高分历史机会",
            url="https://example.com/high",
            source_id="competition",
            source_name="Competition",
            source_group="competition",
            source_pack="competition_pack",
            category="竞赛",
            score=90,
            quality_status="accepted",
            quality_score=90,
        ),
    ]

    rendered = render_history_email(items, {}, total_count=2)

    assert "历史机会汇总" in rendered["subject"]
    assert "低分历史机会也要发送" in rendered["text"]
    assert "高分历史机会" in rendered["html"]
    assert "质量状态概览" in rendered["text"]
    assert len(rendered["eligible"]) == 2
