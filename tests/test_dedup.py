from radar.dedup import merge_duplicates
from radar.models import Opportunity


def _opp(title: str, url: str = "") -> Opportunity:
    return Opportunity(
        title=title,
        url=url,
        source_id="test",
        source_name="Test",
        source_group="competition",
        content="AI 算法 挑战赛",
    )


def test_merge_duplicates_by_similar_title():
    items = [
        _opp("关于举办第十二届华为软件精英挑战赛的通知", "https://example.com/a"),
        _opp("第十二届华为软件精英挑战赛报名启动", "https://example.com/b"),
    ]

    merged = merge_duplicates(items)

    assert len(merged) == 1
    assert "华为软件精英挑战赛" in merged[0].title
