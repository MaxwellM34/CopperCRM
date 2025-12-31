#!/usr/bin/env python3
"""
Simple CSV importer:
- Upload a CSV (same columns as legacy leads.csv).
- Stores rows into imported_leads table (as JSON).
- Lets you download a blank template.
UI matches Copper theme.
"""
import io
import csv
from flask import Flask, request, jsonify, send_file
from pathlib import Path

from email_db import save_imported_leads

app = Flask(__name__)

COLUMNS = [
    "First Name","Last Name","Job Title","Company","Personal Email","Work Email",
    "Work Email Status","Work Email Quality","Work Email Confidence","Primary Work Email Source",
    "Work Email Service Provider","Catch-all Status","Person Address","Country","Seniority",
    "Departments","Personal LinkedIn","Profile Summary","Company LinkedIn","Industries",
    "Company Summary","Company Keywords","Website","# Employees","Phone","Company Address",
    "Company City","Company State","Company Country","Company Phone","Company Email",
    "Technologies","Latest Funding","Latest Funding Amount","Last Raised At","Facebook",
    "Twitter","Youtube","Instagram","Annual Revenue"
]

@app.route("/template")
def template():
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=COLUMNS)
    writer.writeheader()
    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode("utf-8")),
        mimetype="text/csv",
        as_attachment=True,
        download_name="leads_template.csv",
    )


@app.route("/upload", methods=["POST"])
def upload():
    if "file" not in request.files:
        return jsonify({"error": "no file"}), 400
    f = request.files["file"]
    if not f.filename:
        return jsonify({"error": "empty filename"}), 400
    try:
        stream = io.StringIO(f.stream.read().decode("utf-8"))
        reader = csv.DictReader(stream)
        rows = []
        for row in reader:
            normalized = {col: row.get(col, "") for col in COLUMNS}
            rows.append(normalized)
        save_imported_leads(rows)
        return jsonify({"ok": True, "rows_imported": len(rows)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/")
def index():
    return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Copper CSV Importer</title>
    <style>
        body {{
            margin: 0; padding: 0;
            font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            background: #0b1220; color: #e5e7eb;
            display: flex; flex-direction: column; align-items: center;
        }}
        .container {{
            width: 100%; max-width: 800px; margin-top: 30px;
            background: #0f172a; border: 1px solid #1f2937; border-radius: 12px;
            padding: 20px; box-shadow: 0 14px 40px rgba(15, 23, 42, 0.8);
        }}
        h1 {{ color: #f97316; text-align: center; }}
        .card {{ margin-top: 16px; }}
        .btn {{
            background: #22c55e; color: #022c22; border: none;
            padding: 10px 16px; border-radius: 10px; cursor: pointer;
            font-size: 1rem;
        }}
        .btn:disabled {{ opacity: 0.5; cursor: not-allowed; }}
        .link {{ color: #38bdf8; }}
        input[type=file] {{
            margin: 10px 0; color: #e5e7eb;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Upload Leads CSV</h1>
        <p>Columns expected: {", ".join(COLUMNS)}</p>
        <p><a class="link" href="/template">Download blank template</a></p>
        <div class="card">
            <input id="file-input" type="file" accept=".csv" />
            <br>
            <button id="upload-btn" class="btn">Upload</button>
            <div id="status" style="margin-top:10px; color:#9ca3af;"></div>
        </div>
    </div>

    <script>
        const btn = document.getElementById("upload-btn");
        const statusEl = document.getElementById("status");
        btn.onclick = async () => {{
            const fileEl = document.getElementById("file-input");
            if (!fileEl.files.length) {{
                statusEl.textContent = "Please choose a CSV file.";
                return;
            }}
            const formData = new FormData();
            formData.append("file", fileEl.files[0]);
            btn.disabled = true;
            statusEl.textContent = "Uploading...";
            try {{
                const res = await fetch("/upload", {{
                    method: "POST",
                    body: formData
                }});
                const data = await res.json();
                    if (res.ok) {{
                    statusEl.textContent = "Imported " + (data.rows_imported || 0) + " rows.";
                }} else {{
                    statusEl.textContent = data.error || "Upload failed.";
                }}
            }} catch (e) {{
                statusEl.textContent = e.toString();
            }} finally {{
                btn.disabled = false;
            }}
        }};
    </script>
</body>
</html>
"""


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5004, debug=True)
