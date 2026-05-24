from pathlib import Path

from radar.utils.config import enabled_sources, load_config


def test_sources_have_at_least_30_enabled_entries():
    config = load_config(Path("config"))

    assert len(enabled_sources(config)) >= 30
