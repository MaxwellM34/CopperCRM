#!/usr/bin/env python3
"""
Fetch the latest email from a given sender, parse it, and store it into SQLite.

Usage:
  python fetch_and_store_email.py sender@example.com

Env vars (same as other IMAP scripts):
  IMAP_HOST (required)
  IMAP_PORT (default 993)
  IMAP_USER (required)
  IMAP_PASSWORD (required)
  IMAP_FOLDER (default INBOX)
"""
import json
import os
import re
import imaplib
import sys
import time
from email import message_from_bytes
from email.header import decode_header
from typing import Optional, Tuple

from dotenv import load_dotenv

from email_db import save_inbox_email
try:
    from openai import OpenAI
except Exception:
    OpenAI = None

load_dotenv()


def _env(key: str, default: Optional[str] = None, required: bool = False) -> Optional[str]:
    val = os.getenv(key, default)
    if required and not val:
        raise RuntimeError(f"Missing required env var: {key}")
    return val


def _decode_header_value(value: Optional[str]) -> str:
    if not value:
        return ""
    parts = decode_header(value)
    decoded = []
    for text, enc in parts:
        try:
            if isinstance(text, bytes):
                decoded.append(text.decode(enc or "utf-8", errors="replace"))
            else:
                decoded.append(text)
        except Exception:
            decoded.append(str(text))
    return "".join(decoded)


def _strip_html(html: str) -> str:
    text = re.sub(r"(?s)<(script|style).*?>.*?</\\1>", "", html, flags=re.IGNORECASE)
    text = re.sub(r"<br\\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</p>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def _safe_decode(part) -> str:
    try:
        payload = part.get_payload(decode=True)
        charset = part.get_content_charset() or "utf-8"
        return payload.decode(charset, errors="replace").strip()
    except Exception:
        try:
            return part.get_payload().strip()
        except Exception:
            return ""


def _extract_best_text(msg) -> str:
    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            if ctype == "text/plain":
                return _safe_decode(part)
        for part in msg.walk():
            ctype = part.get_content_type()
            if ctype == "text/html":
                return _strip_html(_safe_decode(part))
    else:
        ctype = msg.get_content_type()
        if ctype == "text/plain":
            return _safe_decode(msg)
        if ctype == "text/html":
            return _strip_html(_safe_decode(msg))
    return ""


def _connect_imap() -> imaplib.IMAP4_SSL:
    host = _env("IMAP_HOST", required=True)
    port = int(_env("IMAP_PORT", "993"))
    user = _env("IMAP_USER", required=True)
    pwd = _env("IMAP_PASSWORD", required=True)
    folder = _env("IMAP_FOLDER", "INBOX")

    last_err = None
    for attempt in range(1, 4):
        try:
            m = imaplib.IMAP4_SSL(host, port, timeout=20)
            m.login(user, pwd)
            m.select(folder)
            return m
        except imaplib.IMAP4.abort as e:
            last_err = e
            time.sleep(2 * attempt)
        except Exception as e:
            last_err = e
            break
    raise RuntimeError(f"IMAP connect/login failed: {last_err}")


def _analyze_reply(body: str, replied_to: Optional[dict]) -> dict:
    """
    Use OpenAI to classify reply intent. Falls back to defaults if unavailable.
    """
    defaults = {
        "intent": None,
        "intent_confidence": None,
        "is_human": None,
        "is_auto_reply": False,
        "is_out_of_office": False,
        "is_unsubscriber": False,
        "is_not_interested": False,
        "is_wrong_contact": False,
        "meeting_request": False,
        "contact_schedule": False,
        "meeting_accept": False,
        "forward_or_referral": False,
        "availability_dates": None,
        "meeting_type": None,
        "met_before": None,
        "ask_for_dates": None,
    }

    if not body:
        return defaults

    if not OPENAI_API_KEY or OpenAI is None:
        return defaults

    client = OpenAI(api_key=OPENAI_API_KEY)
    context = replied_to.get("parsed_body") if replied_to else ""
    prompt = (
        "You are an email reply classifier. Return ONLY JSON with these fields:\n"
        "{"
        "\"intent\": string or null,"
        "\"intent_confidence\": number 0-1 or null,"
        "\"is_human\": bool or null,"
        "\"is_auto_reply\": bool,"
        "\"is_out_of_office\": bool,"
        "\"is_unsubscriber\": bool,"
        "\"is_not_interested\": bool,"
        "\"is_wrong_contact\": bool,"
        "\"meeting_request\": bool,"
        "\"contact_schedule\": bool,"
        "\"meeting_accept\": bool,"
        "\"forward_or_referral\": bool,"
        "\"availability_dates\": string or null,"
        "\"meeting_type\": string or null,"
        "\"met_before\": bool or null,"
        "\"ask_for_dates\": bool or null"
        "}\n"
        "No prose, no markdown, JSON only.\n"
        f"Reply body:\n{body[:4000]}\n\nOriginal message (context):\n{context[:4000]}"
    )
    try:
        resp = client.responses.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
            input=[
                {
                    "role": "system",
                    "content": [{"type": "input_text", "text": "Output strict JSON only."}],
                },
                {
                    "role": "user",
                    "content": [{"type": "input_text", "text": prompt}],
                },
            ],
        )
        raw = resp.output_text
        return json.loads(raw)
    except Exception:
        return defaults


def _parse_message(raw: bytes) -> dict:
    msg = message_from_bytes(raw)
    parsed = {
        "subject": _decode_header_value(msg.get("Subject")),
        "from": _decode_header_value(msg.get("From")),
        "to": _decode_header_value(msg.get("To")),
        "date": msg.get("Date"),
        "message_id": msg.get("Message-ID"),
        "in_reply_to": msg.get("In-Reply-To"),
        "parsed_body": _extract_best_text(msg),
    }
    if parsed["parsed_body"] and len(parsed["parsed_body"]) > 5000:
        parsed["parsed_body"] = parsed["parsed_body"][:5000] + "\n\n[truncated]"
    return parsed


def _fetch_by_message_id(message_id: str) -> Optional[dict]:
    """Fetch a message by Message-ID header."""
    if not message_id:
        return None
    m = _connect_imap()
    try:
        # Message-ID often includes <...>; use it as-is in the search.
        status, data = m.search(None, f'(HEADER Message-ID "{message_id}")')
        if status != "OK" or not data or not data[0]:
            return None
        uids = data[0].split()
        # Use the newest match
        for uid in reversed(uids):
            status, msg_data = m.fetch(uid, "(RFC822)")
            if status != "OK" or not msg_data or not msg_data[0]:
                continue
            raw = msg_data[0][1]
            return _parse_message(raw)
        return None
    finally:
        try:
            m.close()
            m.logout()
        except Exception:
            pass


def fetch_latest_from(sender: str) -> Optional[Tuple[bytes, dict]]:
    m = _connect_imap()
    try:
        status, data = m.search(None, f'(FROM "{sender}")')
        if status != "OK" or not data or not data[0]:
            return None
        uids = data[0].split()
        for uid in reversed(uids):  # newest first
            status, msg_data = m.fetch(uid, "(RFC822)")
            if status != "OK" or not msg_data or not msg_data[0]:
                continue
            raw = msg_data[0][1]
            parsed = _parse_message(raw)
            return uid, parsed
        return None
    finally:
        try:
            m.close()
            m.logout()
        except Exception:
            pass


def main():
    if len(sys.argv) != 2:
        print("Usage: python fetch_and_store_email.py sender@example.com", file=sys.stderr)
        sys.exit(1)
    sender = sys.argv[1]
    result = fetch_latest_from(sender)
    if not result:
        print(json.dumps({"ok": False, "error": "no messages found"}, indent=2))
        sys.exit(1)
    _, parsed = result

    replied_to = _fetch_by_message_id(parsed.get("in_reply_to"))

    save_inbox_email(
        sender=parsed["from"],
        recipient=parsed["to"],
        subject=parsed["subject"],
        parsed_body=parsed["parsed_body"],
        message_id=parsed["message_id"],
        folder=os.getenv("IMAP_FOLDER", "INBOX"),
        metadata_json={
            "date": parsed["date"],
            "in_reply_to": parsed["in_reply_to"],
            "stored_at": time.time(),
            "source": "fetch_and_store_email",
            "replied_to": replied_to,
            "analysis": _analyze_reply(parsed["parsed_body"], replied_to),
        },
    )

    print(
        json.dumps(
            {
                "ok": True,
                "stored": True,
                "email": parsed,
                "replied_to": replied_to,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
