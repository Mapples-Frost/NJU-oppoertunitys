from __future__ import annotations

import email
import email.header
import imaplib
import os
from email.message import Message
from typing import Any

from radar.models import Opportunity, SourceResult
from radar.utils.text import normalize_spaces
from radar.utils.url import canonicalize_url
from radar.utils.wechat import extract_wechat_urls


def fetch_imap_email(source: dict[str, Any]) -> SourceResult:
    result = SourceResult(
        source_id=source["id"],
        source_name=source["name"],
        source_type="imap_email",
        source_pack=source.get("source_pack", ""),
        source_domain=source.get("domain", ""),
        source_tier=source.get("source_tier", ""),
    )
    env = _env(source)
    missing = [key for key, value in env.items() if not value]
    if missing:
        result.error = None
        return result
    try:
        port = int(env["IMAP_PORT"])
        klass = imaplib.IMAP4_SSL if port == 993 else imaplib.IMAP4
        with klass(env["IMAP_HOST"], port) as client:
            client.login(env["IMAP_USER"], env["IMAP_PASS"])
            client.select(source.get("mailbox", "INBOX"))
            status, data = client.search(None, source.get("search", "UNSEEN"))
            if status != "OK":
                raise RuntimeError("IMAP search failed")
            ids = data[0].split()[-int(source.get("max_items", 10)) :]
            for msg_id in ids:
                status, message_data = client.fetch(msg_id, "(RFC822)")
                if status != "OK" or not message_data:
                    continue
                raw = message_data[0][1]
                msg = email.message_from_bytes(raw)
                result.items.extend(_message_to_items(msg, source))
    except Exception as exc:
        result.error = str(exc)
    return result


def _env(source: dict[str, Any]) -> dict[str, str]:
    prefix = source.get("env_prefix", "IMAP")
    return {
        "IMAP_HOST": os.getenv(f"{prefix}_HOST", "").strip(),
        "IMAP_PORT": os.getenv(f"{prefix}_PORT", "").strip(),
        "IMAP_USER": os.getenv(f"{prefix}_USER", "").strip(),
        "IMAP_PASS": os.getenv(f"{prefix}_PASS", "").strip(),
    }


def _message_to_items(msg: Message, source: dict[str, Any]) -> list[Opportunity]:
    subject = normalize_spaces(str(email.header.make_header(email.header.decode_header(msg.get("Subject", "")))))
    body = _message_body(msg)
    urls = extract_wechat_urls(body)
    if not urls:
        for token in body.split():
            url = canonicalize_url(token)
            if url:
                urls.append(url)
    if not urls:
        return [
            Opportunity(
                title=subject or "邮件转发机会",
                url=None,
                source_id=source["id"],
                source_name=source["name"],
                source_group=source.get("group", "email"),
                source_pack=source.get("source_pack", ""),
                source_domain=source.get("domain", ""),
                source_tier=source.get("source_tier", ""),
                published_at=msg.get("Date"),
                content=body,
                category=source.get("category_hint", "邮件转发"),
                tags=list(source.get("tags", [])),
                raw={"source_weight": source.get("weight", 1.0)},
            )
        ]
    items = []
    for url in list(dict.fromkeys(urls)):
        items.append(
            Opportunity(
                title=subject or "邮件转发链接",
                url=url,
                source_id=source["id"],
                source_name=source["name"],
                source_group=source.get("group", "email"),
                source_pack=source.get("source_pack", ""),
                source_domain=source.get("domain", ""),
                source_tier=source.get("source_tier", ""),
                published_at=msg.get("Date"),
                content=body,
                category=source.get("category_hint", "邮件转发"),
                tags=list(source.get("tags", [])),
                raw={"source_weight": source.get("weight", 1.0)},
            )
        )
    return items


def _message_body(msg: Message) -> str:
    chunks: list[str] = []
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            if content_type not in {"text/plain", "text/html"}:
                continue
            payload = part.get_payload(decode=True)
            if payload:
                chunks.append(payload.decode(part.get_content_charset() or "utf-8", errors="ignore"))
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            chunks.append(payload.decode(msg.get_content_charset() or "utf-8", errors="ignore"))
    return normalize_spaces(" ".join(chunks))
