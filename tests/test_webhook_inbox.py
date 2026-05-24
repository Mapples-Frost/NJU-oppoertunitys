from pathlib import Path

from radar.fetchers.webhook_inbox_fetcher import fetch_webhook_inbox


def test_fetch_webhook_inbox_reads_jsonl(tmp_path: Path):
    inbox = tmp_path / "inbox.jsonl"
    inbox.write_text(
        '{"title": "公众号竞赛", "url": "https://mp.weixin.qq.com/s/abc?x=1", "content": "AI 竞赛"}\n',
        encoding="utf-8",
    )
    source = {
        "id": "webhook",
        "name": "Webhook",
        "type": "webhook_inbox",
        "group": "wechat",
        "source_pack": "wechat_pack",
        "domain": "wechat",
        "source_tier": "core",
        "path": "inbox.jsonl",
        "tags": ["微信公众号"],
        "weight": 1.0,
    }

    result = fetch_webhook_inbox(source, tmp_path)

    assert result.ok
    assert len(result.items) == 1
    assert result.items[0].url == "https://mp.weixin.qq.com/s/abc"
    assert result.items[0].source_pack == "wechat_pack"
