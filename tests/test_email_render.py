from radar.mailer.render_email import render_email
from radar.models import Opportunity, RunSummary


def test_render_email_includes_items_and_failures():
    run = RunSummary(id="1", started_at="2026-05-24T08:00:00+08:00", new_items=1, total_sources=2, successful_sources=1)
    run.pack_stats = {"competition_pack": {"total": 2, "successful": 1, "failed": 1, "items": 1, "new_items": 1}}
    item = Opportunity(
        id="x",
        title="华为软件精英挑战赛",
        url="https://example.com",
        source_id="huawei",
        source_name="华为",
        source_group="enterprise",
        category="企业开发者赛事",
        score=91,
        summary="AI 算法赛事。",
    )

    rendered = render_email(
        [item],
        run,
        [{"source_id": "bad", "source_name": "坏源", "error": "HTTP 403"}],
        {"subject_template": "[NJU Opportunity Radar] {date}: {count}"},
        {"email_thresholds": {"include": 45, "high_priority": 80}},
    )

    assert "华为软件精英挑战赛" in rendered["text"]
    assert "competition_pack" in rendered["text"]
    assert "坏源" in rendered["html"]
    assert len(rendered["eligible"]) == 1
