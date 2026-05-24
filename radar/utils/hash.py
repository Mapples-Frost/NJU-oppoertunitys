from __future__ import annotations

import hashlib


def stable_hash(value: str, length: int = 32) -> str:
    digest = hashlib.sha256(value.encode("utf-8", errors="ignore")).hexdigest()
    return digest[:length]
