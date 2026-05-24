from radar.utils.wechat import extract_wechat_urls, normalize_wechat_url, parse_wechat_article_html
from radar.fetchers.wechat_article_fetcher import _load_urls


def test_normalize_wechat_url_keeps_stable_identity_params():
    url = (
        "https://mp.weixin.qq.com/s?__biz=abc&mid=1&idx=2&sn=xyz"
        "&chksm=ok&utm_source=x#wechat_redirect"
    )

    assert normalize_wechat_url(url) == "https://mp.weixin.qq.com/s?__biz=abc&mid=1&idx=2&sn=xyz&chksm=ok"


def test_extract_wechat_urls_deduplicates_links():
    text = "看这个 https://mp.weixin.qq.com/s/abc?x=1 和 https://mp.weixin.qq.com/s/abc?x=2"

    assert extract_wechat_urls(text) == ["https://mp.weixin.qq.com/s/abc"]


def test_parse_wechat_article_html():
    html = """
    <html>
      <body>
        <h1 id="activity-name">AI 竞赛报名通知</h1>
        <span id="js_name">南大科创</span>
        <em id="publish_time">2026-05-24</em>
        <div id="js_content">报名截止至2026年6月15日，面向机器人和算法方向。</div>
      </body>
    </html>
    """

    parsed = parse_wechat_article_html(html, "https://mp.weixin.qq.com/s/abc?from=timeline")

    assert parsed["title"] == "AI 竞赛报名通知"
    assert parsed["account"] == "南大科创"
    assert "机器人和算法" in parsed["content"]
    assert parsed["url"] == "https://mp.weixin.qq.com/s/abc"


def test_wechat_article_loader_ignores_fenced_examples(tmp_path):
    path = tmp_path / "wechat.md"
    path.write_text(
        """
```text
https://mp.weixin.qq.com/s/example
```

真实链接：https://mp.weixin.qq.com/s/real
""",
        encoding="utf-8",
    )

    urls = _load_urls({"path": "wechat.md"}, tmp_path)

    assert urls == ["https://mp.weixin.qq.com/s/real"]
