from __future__ import annotations

import os
import uuid
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr

import boto3


def _ses_client():
    region = os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION") or "us-east-1"
    return boto3.client("ses", region_name=region)


def _build_message_id(domain: str | None) -> str:
    safe_domain = domain or "mail.local"
    return f"<{uuid.uuid4().hex}@{safe_domain}>"


def _strip_subject_prefix(subject: str) -> str:
    subject = subject.strip()
    if subject.lower().startswith("re:"):
        return subject[3:].strip()
    return subject


def normalize_subject(subject: str | None, fallback: str = "Quick question") -> str:
    if not subject:
        return fallback
    trimmed = subject.strip()
    return trimmed or fallback


def build_reply_subject(subject: str | None, fallback: str = "Quick question") -> str:
    base = normalize_subject(subject, fallback)
    base = _strip_subject_prefix(base)
    return f"Re: {base}"


def build_raw_email(
    *,
    from_email: str,
    from_name: str | None,
    to_email: str,
    subject: str,
    text_body: str,
    html_body: str | None,
    reply_to: str | None = None,
    in_reply_to: str | None = None,
    references: str | None = None,
    list_unsubscribe: str | None = None,
    message_id: str | None = None,
) -> tuple[bytes, str]:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = formataddr((from_name or "", from_email))
    msg["To"] = to_email
    if reply_to:
        msg["Reply-To"] = reply_to
    if in_reply_to:
        msg["In-Reply-To"] = in_reply_to
    if references:
        msg["References"] = references
    if list_unsubscribe:
        msg["List-Unsubscribe"] = f"<{list_unsubscribe}>"
        msg["List-Unsubscribe-Post"] = "List-Unsubscribe=One-Click"

    header_message_id = message_id or _build_message_id(from_email.split("@")[-1] if "@" in from_email else None)
    msg["Message-ID"] = header_message_id

    msg.attach(MIMEText(text_body, "plain", "utf-8"))
    if html_body:
        msg.attach(MIMEText(html_body, "html", "utf-8"))

    return msg.as_bytes(), header_message_id


def send_raw_email(
    *,
    raw_bytes: bytes,
    source: str,
    to_email: str,
    configuration_set: str | None = None,
) -> str:
    client = _ses_client()
    payload = {
        "Source": source,
        "Destinations": [to_email],
        "RawMessage": {"Data": raw_bytes},
    }
    if configuration_set:
        payload["ConfigurationSetName"] = configuration_set
    response = client.send_raw_email(**payload)
    return response.get("MessageId") or ""
