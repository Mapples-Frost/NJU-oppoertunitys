from radar.classifiers.rule_classifier import classify
from radar.models import Opportunity
from radar.quality_gate import build_quality_report, evaluate_quality
from radar.rankers.opportunity_ranker import rank


PROFILE = {
    "interests": ["AI", "算法竞赛", "机器人", "科研训练", "南京大学"],
    "audience": ["本科生", "大学生", "南京大学"],
    "preferred_categories": ["AI / 算法竞赛"],
    "exclude": ["产品介绍", "办公系统"],
}

QUALITY = {
    "quality_gate": {"min_quality_score": 45, "demote_below": 58, "actionability_min": 12, "audience_fit_min": 6},
    "action_terms": ["报名", "投稿", "招募", "赛题", "deadline", "challenge", "competition"],
    "strong_action_terms": ["报名开启", "call for papers"],
    "background_terms": ["AI", "大模型", "平台"],
    "hard_reject_terms": ["章程", "办公系统", "English"],
    "product_terms": ["AI 助理", "百炼大模型", "产品"],
    "reject_url_parts": ["/modelstudio", "/ai-assistant", "/site/term"],
    "demote_terms": ["讲座"],
    "quality_sources": {"prefer": ["datafountain"], "demote": []},
}


def _ranked(item: Opportunity) -> Opportunity:
    keywords = {"positive": {"high": ["AI", "算法", "机器人"], "medium": ["竞赛", "挑战赛"], "low": []}, "negative": []}
    scoring = {"keyword_weights": {"high": 40, "medium": 24, "low": 10}, "organizers": {"top": [], "medium": []}}
    item = evaluate_quality(item, PROFILE, QUALITY, {"reject": [], "boost": [], "mute_sources": [], "prefer_sources": []})
    return rank(classify(item), keywords, scoring, PROFILE, QUALITY, {})


def test_product_page_is_rejected_and_capped():
    item = _ranked(
        Opportunity(
            title="百炼大模型",
            url="https://developer.aliyun.com/modelstudio",
            source_id="alibaba",
            source_name="阿里云开发者",
            source_group="enterprise",
            content="AI 大模型平台产品介绍",
        )
    )

    assert item.quality_status == "rejected"
    assert item.reject_reason in {"hard_reject_url", "product_or_marketing_page"}
    assert item.score <= 20


def test_actionable_competition_is_accepted():
    item = _ranked(
        Opportunity(
            title="AI 算法挑战赛报名开启",
            url="https://www.datafountain.cn/competitions/999",
            source_id="datafountain",
            source_name="DataFountain",
            source_group="competition",
            source_pack="competition_pack",
            content="面向大学生开放，包含赛题、报名和作品提交，deadline 2026-06-10。",
            tags=["AI", "算法竞赛"],
        )
    )

    assert item.quality_status == "accepted"
    assert item.actionability_score >= 12
    assert item.score >= 70


def test_feedback_reject_and_boost_are_applied():
    rejected = evaluate_quality(
        Opportunity(
            title="某个噪音机会",
            url="https://example.com/noise",
            source_id="manual",
            source_name="Manual",
            source_group="manual",
            content="报名 AI 算法竞赛",
        ),
        PROFILE,
        QUALITY,
        {"reject": ["噪音机会"], "boost": [], "mute_sources": [], "prefer_sources": []},
    )
    boosted = evaluate_quality(
        Opportunity(
            title="AI 算法挑战赛报名",
            url="https://example.com/game",
            source_id="manual",
            source_name="Manual",
            source_group="manual",
            content="面向南京大学本科生，报名开启。",
        ),
        PROFILE,
        QUALITY,
        {"reject": [], "boost": ["南京大学"], "mute_sources": [], "prefer_sources": []},
    )

    assert rejected.quality_status == "rejected"
    assert rejected.reject_reason == "user_reject"
    assert boosted.quality_score >= 45


def test_generic_competition_listing_is_rejected():
    item = evaluate_quality(
        Opportunity(
            title="Competitions",
            url="https://www.drivendata.org/competitions",
            source_id="drivendata_competitions",
            source_name="DrivenData Competitions",
            source_group="competition",
            source_pack="competition_pack",
            content="Browse data science competitions and challenges.",
        ),
        PROFILE,
        QUALITY,
        {"reject": [], "boost": [], "mute_sources": [], "prefer_sources": []},
    )

    assert item.quality_status == "rejected"
    assert item.reject_reason == "generic_listing_page"


def test_quality_report_counts_rejections():
    items = [
        Opportunity(title="A", source_id="s", source_name="S", source_group="manual", quality_status="accepted"),
        Opportunity(
            title="B",
            source_id="s",
            source_name="S",
            source_group="manual",
            quality_status="rejected",
            reject_reason="product_or_marketing_page",
        ),
    ]

    report = build_quality_report(items, [])

    assert report["accepted"] == 1
    assert report["rejected"] == 1
    assert report["reject_reasons"]["product_or_marketing_page"] == 1
