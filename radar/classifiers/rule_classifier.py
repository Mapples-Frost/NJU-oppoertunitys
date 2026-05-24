from __future__ import annotations

from radar.models import Opportunity
from radar.utils.text import first_sentence, normalize_spaces


def classify(opportunity: Opportunity) -> Opportunity:
    text = opportunity.combined_text.lower()
    category = opportunity.category or "可选机会"

    if any(word.lower() in text for word in ["robocup", "机器人", "智能车", "自动化", "控制", "具身"]):
        category = "机器人 / 自动化 / 智能车"
    elif any(word.lower() in text for word in ["竞赛", "大赛", "挑战赛", "competition", "kaggle", "天池", "datafountain", "算法"]):
        category = "AI / 算法竞赛"
    elif any(word in text for word in ["华为", "阿里", "腾讯", "字节", "百度", "讯飞", "开发者", "企业"]):
        category = "企业开发者赛事"
    elif any(word in text for word in ["讲座", "报告", "论坛", "沙龙", "seminar"]):
        category = "校内讲座 / 学术报告"
    elif any(word in text for word in ["大创", "科研训练", "项目招募", "实验室", "招募", "课题"]):
        category = "大创 / 科研训练 / 项目招募"
    elif any(word in text for word in ["志愿", "公益", "培训", "课程"]):
        category = "志愿 / 低优先级活动"

    opportunity.category = category
    if not opportunity.summary:
        opportunity.summary = first_sentence(opportunity.content or opportunity.title)
    if not opportunity.recommended_action:
        opportunity.recommended_action = recommend_action(opportunity)
    opportunity.content = normalize_spaces(opportunity.content)
    return opportunity


def recommend_action(opportunity: Opportunity) -> str:
    category = opportunity.category
    if "竞赛" in category or "赛事" in category:
        return "查看报名要求和赛题，尽快判断是否需要组队。"
    if "机器人" in category or "自动化" in category:
        return "确认方向匹配度，并联系实验室或竞赛队了解组队机会。"
    if "讲座" in category or "报告" in category:
        return "若主题贴合研究方向，加入日程并提前浏览报告人背景。"
    if "科研" in category or "项目" in category:
        return "阅读申请条件，准备简历或项目经历说明。"
    if "志愿" in category:
        return "作为补充机会关注，优先级低于科研和竞赛。"
    return "快速浏览详情，判断是否值得加入待办。"
