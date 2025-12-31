#!/usr/bin/env python3
"""
Inbound approval app (new port) that shows contact info plus an AI summary
of the email thread (not the raw body). Uses inbox_emails table populated by
fetch_and_store_email.py. Approval status is tracked in metadata_json.
"""
import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

from flask import Flask, jsonify, request

try:
    from openai import OpenAI
except Exception:
    OpenAI = None

from mautic_sync import push_approval_status_only, delete_contact_by_email

# Paths
BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parents[1]
STATIC_DIR = PROJECT_ROOT / "static"
DB_PATH = BASE_DIR / "copper_emails.db"

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")

app = Flask(
    __name__,
    static_folder=str(STATIC_DIR),
    static_url_path="/static",
)


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _extract_email_addr(val: str) -> str:
    """
    Extract plain email address from strings like 'Name <email@example.com>'.
    """
    if not val:
        return ""
    if "<" in val and ">" in val:
        inner = val.split("<", 1)[1].split(">", 1)[0]
        return inner.strip()
    return val.strip()


def get_lead_info(conn: sqlite3.Connection, sender: str, recipient: str) -> dict:
    """
    Look up lead metadata from the emails table using lead_email.
    Tries sender, then recipient.
    """
    cur = conn.cursor()
    for candidate in (_extract_email_addr(sender), _extract_email_addr(recipient)):
        if not candidate:
            continue
        cur.execute(
            """
            SELECT lead_name, lead_title, company_name, lead_website
            FROM emails
            WHERE lead_email = ?
            LIMIT 1
            """,
            (candidate,),
        )
        row = cur.fetchone()
        if row:
            return {
                "lead_name": row["lead_name"],
                "lead_title": row["lead_title"],
                "company_name": row["company_name"],
                "lead_website": row["lead_website"],
            }
    return {}


def parse_metadata(row) -> dict:
    raw = row["metadata_json"]
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except Exception:
        return {}


def update_metadata(conn: sqlite3.Connection, row_id: int, metadata: dict):
    conn.execute(
        "UPDATE inbox_emails SET metadata_json = ? WHERE id = ?",
        (json.dumps(metadata), row_id),
    )
    conn.commit()


def summarize_body(body: str, replied_to: Optional[dict]) -> str:
    """
    Summarize the thread using OpenAI. If unavailable, return a trimmed fallback.
    """
    if not body:
        return "(no content)"

    if not OPENAI_API_KEY or OpenAI is None:
        return (body[:800] + "…") if len(body) > 800 else body

    client = OpenAI(api_key=OPENAI_API_KEY)
    parts = [
        "Summarize this email thread in 3-5 sentences. Focus on intent, asks, and next steps.",
        "Do not include salutations or quoted text. Keep it concise.",
        f"Current reply body:\n{body}",
    ]
    if replied_to and replied_to.get("parsed_body"):
        parts.append(f"Original message (context):\n{replied_to['parsed_body']}")

    prompt = "\n\n".join(parts)

    resp = client.responses.create(
        model=OPENAI_MODEL,
        input=[
            {
                "role": "system",
                "content": [
                    {"type": "input_text", "text": "You are an assistant that produces brief summaries of email threads for reviewers. Keep it short and actionable."}
                ],
            },
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": prompt}
                ],
            },
        ],
    )
    return resp.output_text.strip()


def suggest_reply(body: str, summary: str, replied_to: Optional[dict]) -> str:
    """
    Generate a suggested reply. If OpenAI is unavailable, return a generic placeholder.
    """
    if not OPENAI_API_KEY or OpenAI is None:
        return "Thanks for your reply! Let me look into this and get back to you shortly."

    client = OpenAI(api_key=OPENAI_API_KEY)
    parts = [
        "Write a short, helpful reply to this contact. Be concise and friendly. Offer next steps or ask 1 clarifying question.",
        f"Thread summary:\n{summary or '(no summary)'}",
    ]
    if replied_to and replied_to.get("parsed_body"):
        parts.append(f"Original message context:\n{replied_to['parsed_body']}")
    parts.append(f"Latest reply body:\n{body}")

    prompt = "\n\n".join(parts)

    resp = client.responses.create(
        model=OPENAI_MODEL,
        input=[
            {
                "role": "system",
                "content": [
                    {"type": "input_text", "text": "You draft crisp email replies. Keep under 120 words, plain text. No signatures unless explicitly provided."}
                ],
            },
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": prompt}
                ],
            },
        ],
    )
    return resp.output_text.strip()


def detect_not_interested(body: str, summary: str) -> bool:
    """
    Determine if the contact clearly states they are not interested.
    Prefer OpenAI classification; fallback to minimal keywords.
    """
    text = (body or "") + " " + (summary or "")

    if OPENAI_API_KEY and OpenAI is not None:
        client = OpenAI(api_key=OPENAI_API_KEY)
        prompt = (
            "Binary classify this email reply. Respond only 'yes' or 'no'.\n"
            "Yes = the sender explicitly expresses disinterest or wants no further contact.\n"
            "No = anything else (neutral, positive, scheduling, questions, etc.).\n"
            f"\nEmail reply:\n{text[:4000]}"
        )
        try:
            resp = client.responses.create(
                model=OPENAI_MODEL,
                input=[
                    {
                        "role": "system",
                        "content": [{"type": "input_text", "text": "Answer only yes or no."}],
                    },
                    {
                        "role": "user",
                        "content": [{"type": "input_text", "text": prompt}],
                    },
                ],
            )
            answer = (resp.output_text or "").strip().lower()
            return answer.startswith("y")
        except Exception:
            pass

    # Fallback: minimal keyword check
    lower = text.lower()
    return any(k in lower for k in ["not interested", "no longer interested", "unsubscribe", "stop emailing", "do not contact", "leave me alone", "please remove"])


def find_next_pending(conn) -> Optional[Tuple[sqlite3.Row, dict]]:
    """
    Scan inbox_emails newest-first and return the first row without approval_status.
    approval_status is stored inside metadata_json to avoid schema churn.
    """
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, sender, recipient, subject, parsed_body, message_id, folder, fetched_at, metadata_json
        FROM inbox_emails
        ORDER BY fetched_at DESC
        """
    )
    rows = cur.fetchall()
    for row in rows:
        md = parse_metadata(row)
        if md.get("approval_status") is None:
            return row, md
    return None


@app.route("/api/next", methods=["GET"])
def api_next():
    conn = get_db_connection()
    pending = find_next_pending(conn)
    if not pending:
        conn.close()
        return jsonify({"status": "no_pending_emails"}), 200

    row, metadata = pending
    replied_to = metadata.get("replied_to")

    # Ensure we have an AI summary cached
    summary = metadata.get("ai_summary")
    suggested_reply = metadata.get("ai_suggested_reply")

    if not summary:
        summary = summarize_body(row["parsed_body"], replied_to)
        metadata["ai_summary"] = summary
    if not suggested_reply:
        suggested_reply = suggest_reply(row["parsed_body"], summary, replied_to)
        metadata["ai_suggested_reply"] = suggested_reply

    not_interested = metadata.get("ai_not_interested")
    if not_interested is None:
        not_interested = detect_not_interested(row["parsed_body"], summary)
        metadata["ai_not_interested"] = not_interested

    if metadata.get("ai_summary") != summary or metadata.get("ai_suggested_reply") != suggested_reply:
        update_metadata(conn, row["id"], metadata)
    elif metadata.get("ai_not_interested") != not_interested:
        update_metadata(conn, row["id"], metadata)

    lead_info = get_lead_info(conn, row["sender"], row["recipient"])

    conn.close()

    payload = {
        "id": row["id"],
        "sender": row["sender"],
        "recipient": row["recipient"],
        "subject": row["subject"],
        "parsed_body": summary,  # summary for display
        "ai_suggested_reply": suggested_reply,
        "message_id": row["message_id"],
        "folder": row["folder"],
        "fetched_at": row["fetched_at"],
        "replied_to": replied_to,
        "lead_info": lead_info,
        "ai_not_interested": not_interested,
    }
    return jsonify(payload)


@app.route("/api/decision", methods=["POST"])
def api_decision():
    payload = request.get_json(force=True, silent=True) or {}
    email_id = payload.get("id")
    decision = payload.get("decision")
    edited_reply = payload.get("edited_reply") or ""
    if email_id is None or decision not in {"approved", "rejected", "delete"}:
        return jsonify({"error": "Invalid payload"}), 400

    ts = datetime.utcnow().isoformat(timespec="seconds")

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT metadata_json FROM inbox_emails WHERE id = ?
        """,
        (email_id,),
    )
    row = cur.fetchone()
    if row is None:
        conn.close()
        return jsonify({"error": "Email not found"}), 404

    metadata = parse_metadata(row)
    metadata["approval_status"] = decision
    metadata["approval_timestamp"] = ts
    if edited_reply:
        metadata["ai_suggested_reply"] = edited_reply

    update_metadata(conn, email_id, metadata)
    conn.close()

    if decision == "delete":
        try:
            # delete contact in Mautic using sender email
            full_conn = get_db_connection()
            cur2 = full_conn.cursor()
            cur2.execute(
                """
                SELECT sender FROM inbox_emails WHERE id = ?
                """,
                (email_id,),
            )
            row2 = cur2.fetchone()
            lead_email = _extract_email_addr(row2["sender"]) if row2 else ""
            delete_contact_by_email(lead_email)
            full_conn.close()
        except Exception as e:
            print(f"[Mautic] Error deleting contact for id={email_id}: {e}")
        return jsonify({"status": "ok", "id": email_id, "decision": decision})

    # Push status to Mautic (approval status only; no ai_email_2 sent)
    try:
        full_conn = get_db_connection()
        cur2 = full_conn.cursor()
        cur2.execute(
            """
            SELECT sender, recipient, subject, parsed_body, metadata_json
            FROM inbox_emails
            WHERE id = ?
            """,
            (email_id,),
        )
        row2 = cur2.fetchone()
        lead_info = get_lead_info(full_conn, row2["sender"], row2["recipient"]) if row2 else {}
        md2 = parse_metadata(row2) if row2 else {}
        lead_email = _extract_email_addr(row2["sender"]) if row2 else ""

        lead_payload = {
            "lead_email": lead_email,
            "lead_name": lead_info.get("lead_name", ""),
            "lead_title": lead_info.get("lead_title", ""),
            "company_name": lead_info.get("company_name", ""),
            "lead_website": lead_info.get("lead_website", ""),
            # Do not send ai_email_2; only send post_edit_email if you want to persist the edited reply.
            "post_edit_email": edited_reply or md2.get("ai_suggested_reply") or md2.get("ai_summary") or (row2.get("parsed_body") if row2 else ""),
        }
        push_approval_status_only(lead_payload, approval_status=decision)
        full_conn.close()
    except Exception as e:
        print(f"[Mautic] Error updating inbound contact for id={email_id}: {e}")

    return jsonify({"status": "ok", "id": email_id, "decision": decision})


@app.route("/")
def index():
    return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Inbound Reply Review</title>
    <style>
        html, body {{
            margin: 0;
            padding: 0;
            height: 100%;
            font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            background: #0b1220;
            color: #e5e7eb;
        }}
        .app-container {{
            display: flex;
            height: 100vh;
        }}
        .left-panel {{
            flex: 1.4;
            border-right: 1px solid #1f2933;
            display: flex;
            flex-direction: column;
            align-items: center;
            padding: 16px;
            box-sizing: border-box;
        }}
        .right-panel {{
            flex: 1.6;
            padding: 24px;
            box-sizing: border-box;
            overflow-y: auto;
        }}
        .card {{
            width: 100%;
            max-width: 720px;
            min-height: 320px;
            background: #0f172a;
            border-radius: 18px;
            box-shadow: 0 14px 40px rgba(15, 23, 42, 0.8);
            padding: 16px 20px;
            box-sizing: border-box;
            position: relative;
            overflow: hidden;
            border: 1px solid #1f2937;
        }}
        .card-header {{
            font-weight: 600;
            margin-bottom: 8px;
            color: #f97316;
        }}
        .card-body {{
            font-size: 1.1rem;
            line-height: 1.6;
            white-space: pre-wrap;
            color: #e5e7eb;
            max-height: 520px;
            overflow-y: auto;
            padding-right: 6px;
        }}
        .reply-editor {{
            width: 100%;
            min-height: 260px;
            background: #0b1324;
            color: #e5e7eb;
            border: 1px solid #1f2937;
            border-radius: 10px;
            padding: 12px;
            font-size: 1rem;
            line-height: 1.5;
            resize: vertical;
        }}
        .meta-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 12px 24px;
            margin-top: 16px;
        }}
        .meta-item-label {{
            font-size: 1rem;
            color: #9ca3af;
            letter-spacing: 0.05em;
            text-transform: uppercase;
        }}
        .meta-item-value {{
            font-size: 1.2rem;
        }}
        .btn {{
            border: none;
            border-radius: 999px;
            padding: 10px 18px;
            font-size: 1rem;
            cursor: pointer;
            transition: transform 0.07s ease-out, box-shadow 0.07s ease-out, background 0.2s;
            display: inline-flex;
            align-items: center;
            gap: 6px;
        }}
        .btn-approve {{
            background: #22c55e;
            color: #022c22;
            box-shadow: 0 8px 18px rgba(34, 197, 94, 0.4);
        }}
        .btn-reject {{
            background: #ef4444;
            color: #450a0a;
            box-shadow: 0 8px 18px rgba(239, 68, 68, 0.4);
        }}
    </style>
</head>
<body>
    <div class="app-container">
        <div class="left-panel">
            <img src="/static/copper.png"
                 alt="Copper the Cat"
                 style="width: 360px; margin-bottom: 14px; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.4);" />

            <div class="card">
                <div class="card-header" id="card-header">Suggested Reply</div>
                <div style="font-size:0.95rem; color:#9ca3af;" id="card-subheader"></div>
                <div id="ni-banner" style="display:none; background:#7f1d1d; color:#fecdd3; padding:10px; border-radius:8px; margin:8px 0;">
                    Person not interested. Delete contact or send a reply anyway.
                </div>
                <textarea class="reply-editor" id="reply-editor" placeholder="Edit reply before approving...">Loading...</textarea>
                <div style="margin-top:14px; display:flex; gap:10px;">
                    <button id="btn-reject" class="btn btn-reject">Reject</button>
                    <button id="btn-approve" class="btn btn-approve">Approve</button>
                    <button id="btn-delete" class="btn btn-reject" style="background:#7f1d1d;">Delete Contact</button>
                </div>
            </div>
        </div>

        <div class="right-panel">
            <div class="meta-grid">
                <div>
                    <div class="meta-item-label">From</div>
                    <div class="meta-item-value" id="meta-from"></div>
                </div>
                <div>
                    <div class="meta-item-label">To</div>
                    <div class="meta-item-value" id="meta-to"></div>
                </div>
                <div>
                    <div class="meta-item-label">Lead Name</div>
                    <div class="meta-item-value" id="meta-lead-name"></div>
                </div>
                <div>
                    <div class="meta-item-label">Title</div>
                    <div class="meta-item-value" id="meta-title"></div>
                </div>
                <div>
                    <div class="meta-item-label">Company</div>
                    <div class="meta-item-value" id="meta-company"></div>
                </div>
                <div>
                    <div class="meta-item-label">Website</div>
                    <div class="meta-item-value" id="meta-website"></div>
                </div>
                <div>
                    <div class="meta-item-label">Subject</div>
                    <div class="meta-item-value" id="meta-subject"></div>
                </div>
                <div>
                    <div class="meta-item-label">Fetched At</div>
                    <div class="meta-item-value" id="meta-fetched"></div>
                </div>
                <div>
                    <div class="meta-item-label">Message ID</div>
                    <div class="meta-item-value" id="meta-msgid"></div>
                </div>
                <div>
                    <div class="meta-item-label">Folder</div>
                    <div class="meta-item-value" id="meta-folder"></div>
                </div>
            </div>

            <div style="margin-top:20px; font-size:1rem; color:#9ca3af;">Thread summary</div>
            <div style="white-space:pre-wrap; color:#e5e7eb; margin-top:6px;" id="meta-summary"></div>

            <div style="margin-top:20px; font-size:1rem; color:#9ca3af;">Replied-to (context)</div>
            <div style="white-space:pre-wrap; color:#e5e7eb; margin-top:6px;" id="meta-replied"></div>
        </div>
    </div>

    <script>
        let currentEmail = null;

        async function loadNext() {{
            currentEmail = null;
            document.getElementById("reply-editor").value = "Loading...";
            try {{
                const res = await fetch("/api/next");
                const data = await res.json();
                if (data.status === "no_pending_emails") {{
                    document.getElementById("reply-editor").value = "No pending replies.";
                    document.getElementById("card-header").textContent = "All caught up";
                    document.getElementById("card-subheader").textContent = "";
                    return;
                }}
                currentEmail = data;
                render(data);
            }} catch (err) {{
                console.error(err);
                document.getElementById("reply-editor").value = "Error loading reply.";
            }}
        }}

        function render(email) {{
            document.getElementById("card-header").textContent = "Suggested Reply";
            document.getElementById("card-subheader").textContent = (email.sender || "Unknown sender") + " → " + (email.recipient || "");
            document.getElementById("reply-editor").value = email.ai_suggested_reply || "";
            document.getElementById("ni-banner").style.display = email.ai_not_interested ? "block" : "none";

            document.getElementById("meta-from").textContent = email.sender || "";
            document.getElementById("meta-to").textContent = email.recipient || "";
            const lead = email.lead_info || {{}};
            document.getElementById("meta-lead-name").textContent = lead.lead_name || "";
            document.getElementById("meta-title").textContent = lead.lead_title || "";
            document.getElementById("meta-company").textContent = lead.company_name || "";
            document.getElementById("meta-website").textContent = lead.lead_website || "";
            document.getElementById("meta-subject").textContent = email.subject || "";
            document.getElementById("meta-fetched").textContent = email.fetched_at || "";
            document.getElementById("meta-msgid").textContent = email.message_id || "";
            document.getElementById("meta-folder").textContent = email.folder || "";

            document.getElementById("meta-summary").textContent = email.parsed_body || "(No summary)";

            const replied = email.replied_to && email.replied_to.parsed_body
                ? email.replied_to.parsed_body
                : "(No original message found)";
            document.getElementById("meta-replied").textContent = replied;
        }}

        async function decide(decision) {{
            if (!currentEmail) return;
            const edited = document.getElementById("reply-editor").value || "";
            try {{
                await fetch("/api/decision", {{
                    method: "POST",
                    headers: {{ "Content-Type": "application/json" }},
                    body: JSON.stringify({{ id: currentEmail.id, decision, edited_reply: edited }}),
                }});
            }} catch (err) {{
                console.error("decision error", err);
            }}
            loadNext();
        }}

        document.getElementById("btn-approve").addEventListener("click", () => decide("approved"));
        document.getElementById("btn-reject").addEventListener("click", () => decide("rejected"));
        document.getElementById("btn-delete").addEventListener("click", () => decide("delete"));

        loadNext();
    </script>
</body>
</html>
"""


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5003, debug=True)
