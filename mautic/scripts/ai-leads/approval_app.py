#!/usr/bin/env python3
import sqlite3
from pathlib import Path
from datetime import datetime, timezone
from flask import Flask, jsonify, request

# import the helper that talks to Mautic
from mautic_sync import push_email_to_mautic, push_approval_status_only

# BASE_DIR = .../mautic/scripts/ai-leads
BASE_DIR = Path(__file__).resolve().parent

# PROJECT_ROOT = .../mautic
PROJECT_ROOT = BASE_DIR.parents[1]

# STATIC_DIR = .../mautic/static
STATIC_DIR = PROJECT_ROOT / "static"

DB_PATH = BASE_DIR / "copper_emails.db"

print("BASE_DIR     :", BASE_DIR)
print("PROJECT_ROOT :", PROJECT_ROOT)
print("STATIC_DIR   :", STATIC_DIR)
print("DB_PATH      :", DB_PATH)

app = Flask(
    __name__,
    static_folder=str(STATIC_DIR),  # absolute path to mautic/static
    static_url_path="/static",
)


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# -----------------------
# API ROUTES
# -----------------------

@app.route("/api/next", methods=["GET"])
def api_next_email():
    """
    Return the next email that has not been approved/rejected yet.
    We treat approval_status IS NULL as "pending".
    """
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT
            id,
            lead_email,
            lead_name,
            lead_title,
            company_name,
            lead_website,
            post_edit_email,
            prompt_version,
            editor_version,
            scoring_version,
            created_at,
            approval_status,
            approval_timestamp
        FROM emails
        WHERE approval_status IS NULL
        ORDER BY created_at DESC
        LIMIT 1
        """
    )
    row = cur.fetchone()
    conn.close()

    if row is None:
        return jsonify({"status": "no_pending_emails"}), 200

    data = {k: row[k] for k in row.keys()}
    return jsonify(data)


@app.route("/api/decision", methods=["POST"])
def api_decision():
    """
    Body: { "id": <email_id>, "decision": "approved" | "rejected" }

    When decision == "approved":
      - fetch the email row from sqlite
      - send it to Mautic as a contact
      - add it to the Cold Outbound segment (handled inside mautic_sync)
      - then update approval_status/approval_timestamp in sqlite
    """
    payload = request.get_json(force=True, silent=True) or {}
    email_id = payload.get("id")
    decision = payload.get("decision")

    if email_id is None or decision not in {"approved", "rejected"}:
        return jsonify({"error": "Invalid payload"}), 400

    # Use timezone-aware UTC to avoid deprecation warnings and ambiguous timestamps.
    ts = datetime.now(timezone.utc).isoformat(timespec="seconds")

    conn = get_db_connection()
    cur = conn.cursor()

    # Grab the full row so we have all lead data for Mautic
    cur.execute(
        """
        SELECT
            id,
            lead_email,
            lead_name,
            lead_title,
            company_name,
            lead_website,
            post_edit_email,
            prompt_version,
            editor_version,
            scoring_version,
            created_at,
            approval_status,
            approval_timestamp
        FROM emails
        WHERE id = ?
        """,
        (email_id,),
    )
    row = cur.fetchone()

    if row is None:
        conn.close()
        return jsonify({"error": "Email not found"}), 404

    email_data = {k: row[k] for k in row.keys()}

    if decision == "approved":
        try:
            push_email_to_mautic(email_data, approval_status="approved", add_to_segment=True)
        except Exception as e:
            print(f"[Mautic] Error pushing email id={email_id} to Mautic:", e)
    else:
        # For rejected, still record status in Mautic but don't add to segment.
        try:
            push_approval_status_only(email_data, approval_status="rejected")
        except Exception as e:
            print(f"[Mautic] Error updating approval status for id={email_id}:", e)

    # Update approval status in sqlite
    cur.execute(
        """
        UPDATE emails
        SET approval_status = ?, approval_timestamp = ?
        WHERE id = ?
        """,
        (decision, ts, email_id),
    )
    conn.commit()
    conn.close()

    return jsonify({"status": "ok", "id": email_id, "decision": decision})


# -----------------------
# FRONTEND
# -----------------------

@app.route("/")
def index():
    """
    Serve a single-page UI that:
    - Left 1/3: swipe/approve card with email body + ✅/❌
    - Right 2/3: metadata: "Email to (name)" + company link + details
    - Copper the Cat image above the card
    - Tinder-style swipe indicators + big fading ✓ / ✕ flash
    """
    return f"""

<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Copper Email Approvals</title>
    <style>
        html, body {{
            margin: 0;
            padding: 0;
            height: 100%;
            font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            background: #0f172a;
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
            justify-content: top;
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
            max-width: 700px;
            min-height: 300px;
            background: #020617;
            border-radius: 18px;
            box-shadow: 0 14px 40px rgba(15, 23, 42, 0.9);
            padding: 16px 20px;
            box-sizing: border-box;
            position: relative;
            overflow: hidden;
            border: 1px solid #1f2937;
            transition: transform 0.15s ease-out;
        }}
        .card-header {{
            font-weight: 600;
            margin-bottom: 8px;
            color: #f97316;
        }}
        .card-email-to {{
            font-size: 0.9rem;
            color: #9ca3af;
            margin-bottom: 8px;
        }}
        .card-body {{
            font-size: 1.25rem;
            line-height: 1.6;
            white-space: pre-wrap;
            color: #e5e7eb;
            max-height: 480px;
            overflow-y: auto;
            padding-right: 6px;
        }}
        .card-footer {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-top: 10px;
        }}
        .btn {{
            border: none;
            border-radius: 999px;
            padding: 10px 18px;
            font-size: 1rem;
            cursor: pointer;
            transition: transform 0.07s ease-out, box-shadow 0.07s ease-out, background 0.2s;
            display: flex;
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
        .btn:hover {{
            transform: translateY(-1px);
            box-shadow: 0 10px 20px rgba(15, 23, 42, 0.5);
        }}
        .btn:active {{
            transform: translateY(1px) scale(0.98);
            box-shadow: 0 4px 10px rgba(15, 23, 42, 0.7);
        }}
        .btn span.icon {{
            font-size: 1.2rem;
        }}
        .hint-text {{
            margin-top: 8px;
            font-size: 0.8rem;
            color: #64748b;
            text-align: center;
        }}
        .meta-title {{
            font-size: 1.5rem;
            font-weight: 600;
            margin-bottom: 8px;
        }}
        .meta-subtitle {{
            font-size: 1.25rem;
            color: #9ca3af;
            margin-bottom: 16px;
        }}
        .meta-link a {{
            color: #38bdf8;
            text-decoration: none;
        }}
        .meta-link a:hover {{
            text-decoration: underline;
        }}
        .meta-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 12px 24px;
            margin-top: 16px;
        }}
        .meta-item-label {{
            font-size: 1.4rem;
            color: #9ca3af;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}
        .meta-item-value {{
            font-size: 1.4rem;
        }}
        .status-pill {{
            display: inline-flex;
            align-items: center;
            gap: 6px;
            border-radius: 999px;
            padding: 4px 10px;
            font-size: 0.8rem;
        }}
        .status-pending {{
            background: #1f2937;
            color: #e5e7eb;
        }}
        .status-approved {{
            background: #dcfce7;
            color: #166534;
        }}
        .status-rejected {{
            background: #fee2e2;
            color: #991b1b;
        }}
        .no-email-message {{
            text-align: center;
            color: #9ca3af;
        }}

        /* Tinder-style swipe indicators */
        .swipe-indicator {{
            position: absolute;
            top: 18px;
            padding: 6px 14px;
            border-radius: 999px;
            font-weight: 700;
            letter-spacing: 0.08em;
            font-size: 0.9rem;
            border: 2px solid;
            opacity: 0;
            pointer-events: none;
            transition: opacity 0.1s ease-out;
        }}
        .swipe-approve {{
            right: 18px;
            color: #22c55e;
            border-color: #22c55e;
            transform: rotate(12deg);
        }}
        .swipe-reject {{
            left: 18px;
            color: #f97373;
            border-color: #ef4444;
            transform: rotate(-12deg);
        }}

        /* Big fading ✓ / ✕ flash overlay */
        .decision-flash {{
            position: fixed;
            inset: 0;
            display: flex;
            align-items: center;
            justify-content: center;
            pointer-events: none;
            opacity: 0;
            transition: opacity 0.25s ease-out, transform 0.25s ease-out;
            z-index: 40;
        }}
        .decision-flash-inner {{
            padding: 24px 32px;
            border-radius: 999px;
            font-size: 3rem;
            font-weight: 800;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.7);
            display: flex;
            align-items: center;
            gap: 12px;
        }}
        .decision-flash-approve {{
            background: radial-gradient(circle at top left, #bbf7d0, #166534);
            color: #022c22;
        }}
        .decision-flash-reject {{
            background: radial-gradient(circle at top left, #fecaca, #991b1b);
            color: #450a0a;
        }}
        .decision-flash-visible {{
            opacity: 1;
            transform: scale(1.02);
        }}
    </style>
</head>
<body>
    <div class="app-container">
        <div class="left-panel">
            <!-- Copper image -->
            <img src="/static/copper.png"
                 alt="Copper the Cat"
                 style="width: 400px; margin-bottom: 14px; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.4);" />

            <div id="card" class="card">
                <!-- swipe badges -->
                <div id="swipe-approve" class="swipe-indicator swipe-approve">APPROVE</div>
                <div id="swipe-reject" class="swipe-indicator swipe-reject">REJECT</div>

                <div class="card-header">Copper Email Review</div>
                <div class="card-email-to" id="card-email-to">Loading next email...</div>
                <div class="card-body" id="card-body">
                    Please wait while we fetch an email for approval.
                </div>
                <div class="card-footer">
                    <button id="btn-reject" class="btn btn-reject">
                        <span class="icon">❌</span>
                        <span>Reject</span>
                    </button>
                    <button id="btn-approve" class="btn btn-approve">
                        <span class="icon">✅</span>
                        <span>Approve</span>
                    </button>
                </div>
            </div>
            <div class="hint-text">
                Swipe left / press <strong>←</strong> or click ❌ to reject. <br>
                Swipe right / press <strong>→</strong> or click ✅ to approve.
            </div>
        </div>

        <div class="right-panel">
            <div class="meta-title" id="meta-title">Email to &mdash;</div>
            <div class="meta-subtitle" id="meta-subtitle">No email loaded yet.</div>
            <div class="meta-link" id="meta-link"></div>

            <div class="meta-grid">
                <div>
                    <div class="meta-item-label">Lead Email</div>
                    <div class="meta-item-value" id="meta-email"></div>
                </div>
                <div>
                    <div class="meta-item-label">Lead Title</div>
                    <div class="meta-item-value" id="meta-title-role"></div>
                </div>
                <div>
                    <div class="meta-item-label">Prompt Version</div>
                    <div class="meta-item-value" id="meta-prompt-version"></div>
                </div>
                <div>
                    <div class="meta-item-label">Editor Version</div>
                    <div class="meta-item-value" id="meta-editor-version"></div>
                </div>
                <div>
                    <div class="meta-item-label">Scoring Version</div>
                    <div class="meta-item-value" id="meta-scoring-version"></div>
                </div>
                <div>
                    <div class="meta-item-label">Created At</div>
                    <div class="meta-item-value" id="meta-created-at"></div>
                </div>
                <div>
                    <div class="meta-item-label">Approval Status</div>
                    <div class="meta-item-value" id="meta-approval-status"></div>
                </div>
                <div>
                    <div class="meta-item-label">Approval Timestamp</div>
                    <div class="meta-item-value" id="meta-approval-timestamp"></div>
                </div>
            </div>
        </div>
    </div>

    <!-- Big fading decision flash -->
    <div id="decision-flash" class="decision-flash">
        <div id="decision-flash-inner" class="decision-flash-inner">
            <span id="decision-flash-icon">✓</span>
        </div>
    </div>

    <script>
        let currentEmail = null;
        let startX = null;
        let isDragging = false;
        const SWIPE_THRESHOLD = 80; // pixels

        async function loadNextEmail() {{
            currentEmail = null;
            setCardLoadingState();

            try {{
                const res = await fetch("/api/next");
                const data = await res.json();

                if (data.status === "no_pending_emails") {{
                    showNoEmailsState();
                    return;
                }}

                currentEmail = data;
                renderEmail(data);
            }} catch (err) {{
                console.error("Error fetching next email:", err);
                document.getElementById("card-body").textContent =
                    "Error loading email. Check console.";
            }}
        }}

        function setCardLoadingState() {{
            document.getElementById("card-email-to").textContent = "Loading next email...";
            document.getElementById("card-body").textContent = "Please wait while we fetch an email for approval.";
        }}

        function showNoEmailsState() {{
            document.getElementById("card-email-to").textContent = "No more pending emails 🎉";
            document.getElementById("card-body").textContent =
                "You have reviewed all available emails. Come back later when Copper has written more.";
            document.getElementById("meta-title").textContent = "No pending emails";
            document.getElementById("meta-subtitle").textContent = "Everything has been reviewed.";
            document.getElementById("meta-link").innerHTML = "";
            document.getElementById("meta-email").textContent = "";
            document.getElementById("meta-title-role").textContent = "";
            document.getElementById("meta-prompt-version").textContent = "";
            document.getElementById("meta-editor-version").textContent = "";
            document.getElementById("meta-scoring-version").textContent = "";
            document.getElementById("meta-created-at").textContent = "";
            document.getElementById("meta-approval-status").innerHTML =
                '<span class="status-pill status-approved">Done</span>';
            document.getElementById("meta-approval-timestamp").textContent = "";
        }}

        function renderEmail(email) {{
            const name = email.lead_name || "";
            const emailAddr = email.lead_email || "";
            const title = name || emailAddr || "Unknown lead";
            const company = email.company_name || "unknown company";

            document.getElementById("card-email-to").textContent = "Email to " + title;
            document.getElementById("card-body").textContent = email.post_edit_email || "(No email text)";

            document.getElementById("meta-title").textContent = "Email to " + title;
            document.getElementById("meta-subtitle").textContent =
                (email.lead_title || "No job title") + " at " + company;

            if (email.lead_website) {{
                const url = email.lead_website.startsWith("http")
                    ? email.lead_website
                    : "https://" + email.lead_website;
                document.getElementById("meta-link").innerHTML =
                    'Company website: <a href="' + url + '" target="_blank" rel="noreferrer">' + url + "</a>";
            }} else {{
                document.getElementById("meta-link").textContent = "No company website on file.";
            }}

            document.getElementById("meta-email").textContent = emailAddr;
            document.getElementById("meta-title-role").textContent = email.lead_title || "";
            document.getElementById("meta-prompt-version").textContent = email.prompt_version || "";
            document.getElementById("meta-editor-version").textContent = email.editor_version || "";
            document.getElementById("meta-scoring-version").textContent = email.scoring_version || "";
            document.getElementById("meta-created-at").textContent = email.created_at || "";

            const statusEl = document.getElementById("meta-approval-status");
            const tsEl = document.getElementById("meta-approval-timestamp");

            if (!email.approval_status) {{
                statusEl.innerHTML = '<span class="status-pill status-pending">Pending</span>';
                tsEl.textContent = "";
            }} else {{
                if (email.approval_status === "approved") {{
                    statusEl.innerHTML = '<span class="status-pill status-approved">Approved</span>';
                }} else {{
                    statusEl.innerHTML = '<span class="status-pill status-rejected">Rejected</span>';
                }}
                tsEl.textContent = email.approval_timestamp || "";
            }}
        }}

        function flashDecision(decision) {{
            const flash = document.getElementById("decision-flash");
            const inner = document.getElementById("decision-flash-inner");
            const iconSpan = document.getElementById("decision-flash-icon");

            if (decision === "approved") {{
                inner.classList.remove("decision-flash-reject");
                inner.classList.add("decision-flash-approve");
                iconSpan.textContent = "✓";
            }} else {{
                inner.classList.remove("decision-flash-approve");
                inner.classList.add("decision-flash-reject");
                iconSpan.textContent = "✕";
            }}

            flash.classList.add("decision-flash-visible");
            setTimeout(() => {{
                flash.classList.remove("decision-flash-visible");
            }}, 350);
        }}

        async function sendDecision(decision) {{
            if (!currentEmail) return;

            flashDecision(decision);

            try {{
                await fetch("/api/decision", {{
                    method: "POST",
                    headers: {{
                        "Content-Type": "application/json",
                    }},
                    body: JSON.stringify({{
                        id: currentEmail.id,
                        decision: decision,
                    }}),
                }});
            }} catch (err) {{
                console.error("Error sending decision:", err);
            }}

            // Reset card position & swipe indicators
            resetCardTransform();
            hideSwipeIndicators();

            // Immediately fetch next email
            loadNextEmail();
        }}

        function setSwipeIndicator(dx) {{
            const approve = document.getElementById("swipe-approve");
            const reject = document.getElementById("swipe-reject");
            const magnitude = Math.min(Math.abs(dx) / SWIPE_THRESHOLD, 1);

            if (dx > 0) {{
                approve.style.opacity = magnitude.toString();
                reject.style.opacity = "0";
            }} else if (dx < 0) {{
                reject.style.opacity = magnitude.toString();
                approve.style.opacity = "0";
            }} else {{
                approve.style.opacity = "0";
                reject.style.opacity = "0";
            }}
        }}

        function hideSwipeIndicators() {{
            document.getElementById("swipe-approve").style.opacity = "0";
            document.getElementById("swipe-reject").style.opacity = "0";
        }}

        function resetCardTransform() {{
            const cardEl = document.getElementById("card");
            cardEl.style.transition = "transform 0.15s ease-out";
            cardEl.style.transform = "translateX(0px) rotate(0deg)";
            setTimeout(() => {{
                cardEl.style.transition = "transform 0.0s linear";
            }}, 160);
        }}

        // Button handlers
        document.getElementById("btn-approve").addEventListener("click", () => sendDecision("approved"));
        document.getElementById("btn-reject").addEventListener("click", () => sendDecision("rejected"));

        // Keyboard handlers: left/right arrows
        document.addEventListener("keydown", (e) => {{
            if (e.key === "ArrowLeft") {{
                sendDecision("rejected");
            }} else if (e.key === "ArrowRight") {{
                sendDecision("approved");
            }}
        }});

        const cardEl = document.getElementById("card");

        // Touch swipe
        cardEl.addEventListener("touchstart", (e) => {{
            if (e.touches.length !== 1) return;
            isDragging = true;
            startX = e.touches[0].clientX;
            cardEl.style.transition = "transform 0.0s linear";
        }});

        cardEl.addEventListener("touchmove", (e) => {{
            if (!isDragging || startX === null) return;
            const dx = e.touches[0].clientX - startX;
            cardEl.style.transform = "translateX(" + dx * 0.25 + "px) rotate(" + dx * 0.04 + "deg)";
            setSwipeIndicator(dx);
        }});

        cardEl.addEventListener("touchend", (e) => {{
            if (!isDragging || startX === null) return;
            const endX = e.changedTouches[0].clientX;
            const dx = endX - startX;
            isDragging = false;
            startX = null;

            if (Math.abs(dx) > SWIPE_THRESHOLD) {{
                if (dx > 0) {{
                    sendDecision("approved");
                }} else {{
                    sendDecision("rejected");
                }}
            }} else {{
                resetCardTransform();
                hideSwipeIndicators();
            }}
        }});

        // Mouse drag swipe (desktop Tinder vibes)
        cardEl.addEventListener("mousedown", (e) => {{
            isDragging = true;
            startX = e.clientX;
            cardEl.style.transition = "transform 0.0s linear";
        }});

        document.addEventListener("mousemove", (e) => {{
            if (!isDragging || startX === null) return;
            const dx = e.clientX - startX;
            cardEl.style.transform = "translateX(" + dx * 0.25 + "px) rotate(" + dx * 0.04 + "deg)";
            setSwipeIndicator(dx);
        }});

        document.addEventListener("mouseup", (e) => {{
            if (!isDragging || startX === null) return;
            const dx = e.clientX - startX;
            isDragging = false;
            startX = null;

            if (Math.abs(dx) > SWIPE_THRESHOLD) {{
                if (dx > 0) {{
                    sendDecision("approved");
                }} else {{
                    sendDecision("rejected");
                }}
            }} else {{
                resetCardTransform();
                hideSwipeIndicators();
            }}
        }});

        // Initial load
        resetCardTransform();
        hideSwipeIndicators();
        loadNextEmail();
    </script>
</body>
</html>
"""


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
