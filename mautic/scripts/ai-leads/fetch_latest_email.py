#!/usr/bin/env python3
"""
Fetch and parse the most recent email from a given sender.

Usage:
  python fetch_latest_email.py sender@example.com

Environment:
  IMAP_HOST (required)
  IMAP_PORT (default 993)
  IMAP_USER (required)
  IMAP_PASSWORD (required)
  IMAP_FOLDER (default INBOX)
"""
import os
import re
import sys
import imaplib
import time
import json
from email import message_from_bytes
from email.header import decode_header
from typing import Optional, Tuple

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None


def _load_env():
    if load_dotenv:
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


def _connect_imap(index: int) -> imaplib.IMAP4_SSL:
    host = _env("IMAP_HOST", required=True)
    port = int(_env("IMAP_PORT", "993"))
    folder = _env("IMAP_FOLDER", "INBOX")

    # Load and parse array from environment
    accounts_raw = _env("IMAP_ACCOUNTS", required=True)
    accounts = json.loads(accounts_raw)    #type: ignore


    # Validate the index
    if index < 0 or index >= len(accounts):
        raise ValueError(f"IMAP account index {index} is out of range. "
                         f"Available accounts: {len(accounts)}")

    # Pick the selected account
    acct = accounts[index]
    user = acct["user"]
    pwd  = acct["pass"]


    last_err = None
    for attempt in range(1, 4):
        try:
            m = imaplib.IMAP4_SSL(host, port, timeout=20)
            m.login(user, pwd)
            m.select(folder)
            return m
        except imaplib.IMAP4.abort as e:
            last_err = e
            # Temporary/abort errors often clear on retry.
            time.sleep(2 * attempt)
        except Exception as e:
            last_err = e
            break
    raise RuntimeError(f"IMAP connect/login failed: {last_err}")


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
        print("Usage: python fetch_latest_email.py sender@example.com", file=sys.stderr)
        sys.exit(1)
    sender = sys.argv[1]
    _load_env()
    result = fetch_latest_from(sender)
    if not result:
        print(json.dumps({"ok": False, "error": "no messages found"}, indent=2))
        sys.exit(1)
    _, parsed = result
    print(json.dumps({"ok": True, "email": parsed}, indent=2))


if __name__ == "__main__":
    main()
