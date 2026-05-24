from __future__ import annotations

import os
import smtplib
from email.message import EmailMessage


REQUIRED_ENV = ["SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASS", "MAIL_FROM", "MAIL_TO"]


def _require_env() -> dict[str, str]:
    values = {key: os.getenv(key, "").strip() for key in REQUIRED_ENV}
    missing = [key for key, value in values.items() if not value]
    if missing:
        raise RuntimeError(
            "missing SMTP environment variables: "
            + ", ".join(missing)
            + ". Configure them as local env vars or GitHub Secrets."
        )
    return values


def send_email(subject: str, text_body: str, html_body: str) -> None:
    env = _require_env()
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = env["MAIL_FROM"]
    message["To"] = env["MAIL_TO"]
    message.set_content(text_body)
    message.add_alternative(html_body, subtype="html")

    port = int(env["SMTP_PORT"])
    if port == 465:
        with smtplib.SMTP_SSL(env["SMTP_HOST"], port, timeout=30) as smtp:
            smtp.login(env["SMTP_USER"], env["SMTP_PASS"])
            smtp.send_message(message)
    else:
        with smtplib.SMTP(env["SMTP_HOST"], port, timeout=30) as smtp:
            smtp.starttls()
            smtp.login(env["SMTP_USER"], env["SMTP_PASS"])
            smtp.send_message(message)
