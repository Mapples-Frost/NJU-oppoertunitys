from radar.classifiers.rule_classifier import classify
from radar.models import Opportunity
from radar.rankers.opportunity_ranker import rank


def test_classifier_and_ranker_scores_ai_competition():
    opp = Opportunity(
        title="华为软件精英挑战赛报名开启",
        url="https://example.com",
        source_id="huawei",
        source_name="华为",
        source_group="enterprise",
        content="面向 AI 算法工程，提供奖金和证书。",
        tags=["AI", "算法", "企业赛"],
        deadline_at="2026-06-10T23:59:00+08:00",
        raw={"source_weight": 1.3},
    )
    keywords = {"positive": {"high": ["AI", "算法", "华为软件精英"], "medium": ["挑战赛"], "low": []}, "negative": []}
    scoring = {
        "keyword_weights": {"high": 40, "medium": 24, "low": 10},
        "organizers": {"top": ["华为"], "medium": []},
    }

    ranked = rank(classify(opp), keywords, scoring)

    assert ranked.category == "AI / 算法竞赛"
    assert ranked.score >= 80
