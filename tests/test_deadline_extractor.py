from datetime import datetime
from zoneinfo import ZoneInfo

from radar.extractors.deadline_extractor import extract_dates


TZ = ZoneInfo("Asia/Shanghai")


def test_extract_chinese_deadline_without_year_uses_current_year():
    result = extract_dates("报名通知", "报名截止至6月15日24:00", now=datetime(2026, 5, 24, tzinfo=TZ))

    assert result["deadline_at"].startswith("2026-06-15")
    assert result["date_confidence"] == "medium"


def test_extract_past_date_rolls_to_next_year_with_low_confidence():
    result = extract_dates("报名通知", "报名截止至2026年5月20日", now=datetime(2026, 5, 24, tzinfo=TZ))

    assert result["deadline_at"].startswith("2027-05-20")
    assert result["date_confidence"] == "low"
