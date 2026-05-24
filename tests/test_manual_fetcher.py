from radar.fetchers.manual_fetcher import parse_manual_markdown


def test_parse_manual_markdown():
    source = {"id": "manual", "name": "手动入口", "group": "manual", "tags": ["手动"], "weight": 1.0}
    text = """
## RoboCup 报名提醒
链接：https://example.com/robocup?utm_source=x
来源：微信群
内容：机器人竞赛，适合视觉和控制方向。
截止：2026-06-15
"""

    items = parse_manual_markdown(text, source)

    assert len(items) == 1
    assert items[0].title == "RoboCup 报名提醒"
    assert items[0].url == "https://example.com/robocup"
    assert "机器人竞赛" in items[0].content


def test_parse_manual_markdown_ignores_fenced_examples():
    source = {"id": "manual", "name": "手动入口", "group": "manual", "tags": ["手动"], "weight": 1.0}
    text = """
# 手动机会入口

```markdown
## 示例机会
链接：https://example.com
内容：这只是格式示例。
```
"""

    assert parse_manual_markdown(text, source) == []
