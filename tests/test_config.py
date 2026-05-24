from pathlib import Path

from radar.utils.config import enabled_sources, load_config


def test_sources_have_at_least_30_enabled_entries():
    config = load_config(Path("config"))

    assert len(enabled_sources(config)) >= 30


def test_v2_source_pack_coverage():
    config = load_config(Path("config"))
    sources = enabled_sources(config)
    by_pack: dict[str, int] = {}
    by_type: dict[str, int] = {}
    for source in sources:
        by_pack[source["source_pack"]] = by_pack.get(source["source_pack"], 0) + 1
        by_type[source["type"]] = by_type.get(source["type"], 0) + 1

    assert len(sources) >= 80
    assert by_pack["competition_pack"] >= 35
    assert by_pack["research_pack"] >= 25
    assert by_pack["wechat_pack"] >= 4
    assert by_type["wechat_article"] >= 1
    assert by_type["imap_email"] >= 1
    assert by_type["webhook_inbox"] >= 1


def test_v3_quality_config_is_loaded():
    config = load_config(Path("config"))

    assert config["profile"]["interests"]
    assert config["quality"]["quality_gate"]["min_quality_score"] >= 1
    assert "reject" in config["feedback"]
