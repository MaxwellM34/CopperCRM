from __future__ import annotations

import email
import imaplib
from datetime import datetime, timezone
from email.header import decode_header
from email.utils import parsedate_to_datetime
from typing import Iterable


def _connect_imap(host: str, port: int | None, use_ssl: bool) -> imaplib.IMAP4:
    if use_ssl:
        return imaplib.IMAP4_SSL(host, port or 993)
    return imaplib.IMAP4(host, port or 143)


def _decode_header(value: str | None) -> str:
    if not value:
        return ""
    parts = decode_header(value)
    decoded = []
    for text, encoding in parts:
        if isinstance(text, bytes):
            try:
                decoded.append(text.decode(encoding or "utf-8", errors="ignore"))
            except Exception:
                decoded.append(text.decode("utf-8", errors="ignore"))
        else:
            decoded.append(text)
    return "".join(decoded)


def _extract_text(msg: email.message.Message) -> str:
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = part.get("Content-Disposition", "")
            if content_type == "text/plain" and "attachment" not in content_disposition.lower():
                payload = part.get_payload(decode=True)
                if payload is None:
                    continue
                return payload.decode(part.get_content_charset() or "utf-8", errors="ignore")
        for part in msg.walk():
            if part.get_content_type() == "text/html":
                payload = part.get_payload(decode=True)
                if payload is None:
                    continue
                return payload.decode(part.get_content_charset() or "utf-8", errors="ignore")
        return ""
    payload = msg.get_payload(decode=True)
    if payload is None:
        return ""
    return payload.decode(msg.get_content_charset() or "utf-8", errors="ignore")


def _parse_date(value: str | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    try:
        dt = parsedate_to_datetime(value)
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return datetime.now(timezone.utc)


def fetch_new_messages(
    *,
    host: str,
    port: int | None,
    use_ssl: bool,
    username: str,
    password: str,
    folder: str,
    last_uid: int | None = None,
) -> tuple[list[dict], int | None]:
    conn = _connect_imap(host, port, use_ssl)
    conn.login(username, password)
    conn.select(folder)

    if last_uid:
        search_criteria = f"(UID {last_uid + 1}:*)"
    else:
        search_criteria = "ALL"

    _, data = conn.uid("search", None, search_criteria)
    uids = [int(uid) for uid in data[0].split()] if data and data[0] else []

    messages: list[dict] = []
    newest_uid = last_uid
    for uid in uids:
        _, msg_data = conn.uid("fetch", str(uid), "(RFC822)")
        if not msg_data or not msg_data[0]:
            continue
        raw = msg_data[0][1]
        msg = email.message_from_bytes(raw)
        from_addr = email.utils.parseaddr(msg.get("From"))[1]
        to_addr = email.utils.parseaddr(msg.get("To"))[1]
        subject = _decode_header(msg.get("Subject"))
        message_id = msg.get("Message-ID") or ""
        in_reply_to = msg.get("In-Reply-To") or ""
        references = msg.get("References") or ""
        date = _parse_date(msg.get("Date"))
        body = _extract_text(msg)
        messages.append(
            {
                "uid": uid,
                "from": from_addr,
                "to": to_addr,
                "subject": subject,
                "message_id": message_id,
                "in_reply_to": in_reply_to,
                "references": references,
                "date": date,
                "body": body,
            }
        )
        newest_uid = uid if newest_uid is None else max(newest_uid, uid)

    conn.logout()
    return messages, newest_uid


def fetch_thread_messages(
    *,
    host: str,
    port: int | None,
    use_ssl: bool,
    username: str,
    password: str,
    inbox_folder: str,
    sent_folder: str | None,
    lead_email: str,
    max_messages: int = 12,
) -> list[dict]:
    conn = _connect_imap(host, port, use_ssl)
    conn.login(username, password)
    folders = [f for f in [inbox_folder, sent_folder] if f]

    messages: list[dict] = []
    for folder in folders:
        conn.select(folder)
        if folder == inbox_folder:
            criteria = f'(FROM "{lead_email}")'
        else:
            criteria = f'(TO "{lead_email}")'
        _, data = conn.search(None, criteria)
        msg_ids = data[0].split() if data and data[0] else []
        for msg_id in msg_ids[-max_messages:]:
            _, msg_data = conn.fetch(msg_id, "(RFC822)")
            if not msg_data or not msg_data[0]:
                continue
            raw = msg_data[0][1]
            msg = email.message_from_bytes(raw)
            from_addr = email.utils.parseaddr(msg.get("From"))[1]
            to_addr = email.utils.parseaddr(msg.get("To"))[1]
            subject = _decode_header(msg.get("Subject"))
            message_id = msg.get("Message-ID") or ""
            date = _parse_date(msg.get("Date"))
            body = _extract_text(msg)
            messages.append(
                {
                    "from": from_addr,
                    "to": to_addr,
                    "subject": subject,
                    "message_id": message_id,
                    "date": date,
                    "body": body,
                }
            )

    conn.logout()
    messages.sort(key=lambda m: m.get("date") or datetime.now(timezone.utc))
    return messages


def render_thread_text(messages: Iterable[dict], max_chars: int = 8000) -> str:
    parts: list[str] = []
    for msg in messages:
        date = msg.get("date")
        date_str = date.astimezone(timezone.utc).isoformat() if isinstance(date, datetime) else ""
        parts.append(
            "\n".join(
                [
                    f"From: {msg.get('from', '')}",
                    f"To: {msg.get('to', '')}",
                    f"Subject: {msg.get('subject', '')}",
                    f"Date: {date_str}",
                    "",
                    (msg.get("body") or "").strip(),
                ]
            )
        )
    joined = "\n\n---\n\n".join(parts).strip()
    if len(joined) > max_chars:
        return joined[-max_chars:]
    return joined
