import pytest

from radar.mailer.send_email import REQUIRED_ENV, send_email


def test_send_email_reports_missing_smtp_env(monkeypatch):
    for key in REQUIRED_ENV:
        monkeypatch.delenv(key, raising=False)

    with pytest.raises(RuntimeError, match="missing SMTP environment variables"):
        send_email("subject", "text", "<p>html</p>")
