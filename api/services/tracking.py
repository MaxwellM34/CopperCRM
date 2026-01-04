from __future__ import annotations

import base64
import hashlib
import hmac
import os
import uuid
from typing import Optional


def _secret() -> str:
    value = os.getenv("UNSUBSCRIBE_SECRET", "")
    if not value:
        value = os.getenv("CRM_SECRET", "")
    if not value:
        raise RuntimeError("UNSUBSCRIBE_SECRET (or CRM_SECRET) is not configured")
    return value


def build_tracking_id() -> str:
    return uuid.uuid4().hex


def build_unsubscribe_token(lead_id: int, email: str | None) -> str:
    payload = f"{lead_id}:{email or ''}"
    sig = hmac.new(_secret().encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()
    raw = f"{payload}:{sig}".encode("utf-8")
    token = base64.urlsafe_b64encode(raw).decode("utf-8").rstrip("=")
    return token


def parse_unsubscribe_token(token: str) -> Optional[tuple[int, str | None]]:
    padded = token + "=" * (-len(token) % 4)
    try:
        raw = base64.urlsafe_b64decode(padded.encode("utf-8")).decode("utf-8")
    except Exception:
        return None
    parts = raw.split(":")
    if len(parts) < 3:
        return None
    lead_id_str = parts[0]
    email = parts[1] or None
    sig = parts[-1]
    payload = f"{lead_id_str}:{email or ''}"
    expected = hmac.new(_secret().encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(sig, expected):
        return None
    try:
        lead_id = int(lead_id_str)
    except ValueError:
        return None
    return lead_id, email


def get_public_base_url() -> str:
    return (
        os.getenv("PUBLIC_BASE_URL")
        or os.getenv("PUBLIC_API_BASE")
        or os.getenv("CRM_PUBLIC_URL")
        or "http://localhost:8000"
    ).rstrip("/")


def build_tracking_url(tracking_id: str) -> str:
    return f"{get_public_base_url()}/tracking/pixel/{tracking_id}.gif"


def build_unsubscribe_url(token: str) -> str:
    return f"{get_public_base_url()}/unsubscribe/{token}"
