#!/usr/bin/env python3
"""
Lightweight webhook receiver for Mautic "contact replied to email" actions.

- Accepts a POST from Mautic (JSON).
- Optionally verifies a shared secret header.
- Looks up the latest reply in IMAP for that contact.
- Stores only a parsed/plain version into SQLite (no raw HTML/MIME).
"""
import json
import os
import re
import imaplib
from datetime import datetime, timezone
from email import message_from_bytes
from email.header import decode_header
from typing import Optional, Tuple

from flask import Flask, jsonify, request

from email_db import save_email_reply


app = Flask(__name__)


# -----------------------
# Helpers
# -----------------------

def _env(key: str, default: Optional[str] = None, required: bool = False) -> Optional[str]:
    val = os.getenv(key, default)
    if required and not val:
        raise RuntimeError(f"Missing required env var: {key}")
    return val


def _verify_secret(req) -> bool:
    secret = os.getenv("WEBHOOK_SHARED_SECRET")
    if not secret:
        return True  # no secret set; allow (not recommended in production)
    return req.headers.get("X-Webhook-Secret") == secret


def _decode_header(value: Optional[str]) -> str:
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


def _extract_best_text(msg) -> str:
    """
    Return a parsed/plain text version. Prefers text/plain; falls back to stripped HTML.
    """
    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            if ctype == "text/plain":
                return _safe_decode(part)
        for part in msg.walk():
            ctype = part.get_content_type()
            if ctype == "text/html":
                html = _safe_decode(part)
                return _strip_html(html)
    else:
        ctype = msg.get_content_type()
        if ctype == "text/plain":
            return _safe_decode(msg)
        if ctype == "text/html":
            return _strip_html(_safe_decode(msg))
    return ""


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


def _connect_imap() -> imaplib.IMAP4_SSL:
    host = _env("IMAP_HOST", required=True)
    port = int(_env("IMAP_PORT", "993")) #type: ignore
    user = _env("IMAP_USER", required=True)
    pwd = _env("IMAP_PASSWORD", required=True)

    m = imaplib.IMAP4_SSL(host, port)#type: ignore
    m.login(user, pwd) #type: ignore
    folder = _env("IMAP_FOLDER", "INBOX")
    m.select(folder)#type: ignore
    return m


def _search_latest_reply(contact_email: str, subject_hint: Optional[str]) -> Optional[Tuple[bytes, bytes]]:
    """
    Return the UID and raw message bytes for the latest email from contact_email.
    """
    try:
        m = _connect_imap()
    except imaplib.IMAP4.error as e:
        app.logger.error("IMAP auth failed: %s", e)
        return None
    except Exception as e:
        app.logger.error("IMAP connect failed: %s", e)
        return None
    try:
        status, data = m.search(None, f'(FROM "{contact_email}")')
        if status != "OK" or not data or not data[0]:
            return None

        uids = data[0].split()
        for uid in reversed(uids):  # newest first
            status, msg_data = m.fetch(uid, "(RFC822)")
            if status != "OK" or not msg_data or not msg_data[0]:
                continue
            raw = msg_data[0][1]
            msg = message_from_bytes(raw) #type: ignore

            subj = _decode_header(msg.get("Subject"))
            if subject_hint:
                # Loose match on subject if provided
                if subject_hint.lower() not in subj.lower():
                    continue

            return uid, raw#type: ignore
        return None
    finally:
        try:
            m.close()
            m.logout()
        except Exception:
            pass


def _parse_email(raw: bytes) -> dict:
    msg = message_from_bytes(raw)
    subject = _decode_header(msg.get("Subject"))
    in_reply_to = msg.get("In-Reply-To")
    message_id = msg.get("Message-ID")
    body = _extract_best_text(msg)

    # Trim to avoid storing giant threads; you asked for parsed text only.
    if body and len(body) > 5000:
        body = body[:5000] + "\n\n[truncated]"

    return {
        "subject": subject,
        "in_reply_to": in_reply_to,
        "message_id": message_id,
        "parsed_body": body,
    }


# -----------------------
# Flask route
# -----------------------

@app.route("/mautic/reply", methods=["POST"])
def handle_reply():
    if not _verify_secret(request):
        return jsonify({"error": "unauthorized"}), 401

    payload = request.get_json(force=True, silent=True) or {}
    contact = payload.get("contact") or {}
    contact_email = contact.get("email") or payload.get("email")
    contact_id = str(contact.get("id")) if contact.get("id") is not None else None
    subject_hint = payload.get("subject") or payload.get("emailSubject")

    if not contact_email:
        return jsonify({"error": "contact email missing in webhook"}), 400

    parsed = None
    search_result = _search_latest_reply(contact_email, subject_hint)
    if search_result:
        _, raw = search_result
        parsed = _parse_email(raw)

    save_email_reply(
        contact_email=contact_email,
        contact_id=contact_id, #type: ignore
        subject=parsed["subject"] if parsed else subject_hint, #type: ignore
        parsed_body=parsed["parsed_body"] if parsed else None, #type: ignore
        in_reply_to=parsed["in_reply_to"] if parsed else None, #type: ignore
        message_id=parsed["message_id"] if parsed else None, #type: ignore
        metadata_json={
            "webhook": payload,
            "stored_at": datetime.now(timezone.utc).isoformat(),
            "parsed": bool(parsed),
        },
    )

    return jsonify(
        {
            "ok": True,
            "parsed": bool(parsed),
            "message_id": parsed["message_id"] if parsed else None,
        }
    )


def main():
    port = int(os.getenv("REPLY_SERVER_PORT", "5001"))
    host = os.getenv("REPLY_SERVER_HOST", "0.0.0.0")
    app.run(host=host, port=port)


if __name__ == "__main__":
    main()
