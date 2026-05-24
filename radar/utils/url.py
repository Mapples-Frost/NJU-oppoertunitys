from __future__ import annotations

from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse


TRACKING_PREFIXES = ("utm_",)
TRACKING_KEYS = {
    "spm",
    "fbclid",
    "gclid",
    "yclid",
    "mc_cid",
    "mc_eid",
    "from",
    "share_source",
    "share_token",
}


def canonicalize_url(url: str | None, base_url: str | None = None) -> str:
    if not url:
        return ""
    absolute = urljoin(base_url or "", url.strip())
    parsed = urlparse(absolute)
    if parsed.scheme not in {"http", "https"}:
        return ""
    scheme = "https"
    netloc = parsed.netloc.lower()
    if scheme == "https" and netloc.endswith(":443"):
        netloc = netloc[:-4]
    if scheme == "http" and netloc.endswith(":80"):
        netloc = netloc[:-3]
    query_items = []
    for key, value in parse_qsl(parsed.query, keep_blank_values=False):
        lower_key = key.lower()
        if lower_key in TRACKING_KEYS or lower_key.startswith(TRACKING_PREFIXES):
            continue
        query_items.append((key, value))
    path = parsed.path or "/"
    if path != "/":
        path = path.rstrip("/")
    return urlunparse((scheme, netloc, path, "", urlencode(query_items, doseq=True), ""))
