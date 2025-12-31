#!/usr/bin/env python3
import os
import base64
import json
import subprocess
import urllib.request
import urllib.error

from flask import Flask, request, render_template_string
from dotenv import load_dotenv

# Force-load .env from the project root
load_dotenv("/srv/mautic/.env")

# -----------------------------
# CONFIG
# -----------------------------
MAUTIC_BASE_URL = os.environ.get("MAUTIC_BASE_URL", "http://138.197.156.191/")
# path to the script inside the container
GENERATE_SCRIPT = "/srv/mautic/scripts/ai-leads/generate_and_push.py"
# where we save the uploaded CSV inside the container
LEADS_CSV_PATH = "/srv/mautic/scripts/ai-leads/leads.csv"

UPLOAD_FORM_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Copper Lead Importer</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background: #faf7f2;
            display: flex;
            justify-content: center;
            padding-top: 40px;
        }
        .container {
            background: white;
            width: 520px;
            padding: 30px;
            border-radius: 14px;
            box-shadow: 0px 4px 20px rgba(0,0,0,0.1);
        }
        h2 {
            text-align: center;
            color: #d67f2f;
            margin-bottom: 5px;
        }
        .cat-box {
            text-align: center;
            margin-bottom: 20px;
        }
        .cat-box img {
            width: 160px;
            border-radius: 12px;
            box-shadow: 0px 2px 10px rgba(0,0,0,0.15);
        }
        label {
            font-weight: bold;
            color: #444;
        }
        input[type="text"], input[type="password"], input[type="file"] {
            width: 100%;
            padding: 8px;
            margin-top: 4px;
            border-radius: 6px;
            border: 1px solid #ccc;
        }
        button {
            width: 100%;
            background: #d67f2f;
            color: white;
            padding: 12px;
            font-size: 16px;
            border-radius: 8px;
            border: none;
            cursor: pointer;
        }
        button:hover {
            background: #c36f20;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="cat-box">
            <img src="/static/copper.png" alt="Copper the Cat" />
        </div>

        <h2>Copper Lead Importer</h2>
        <p style="text-align:center;">Upload a CSV to load contacts into Mautic.<br>
        Optional: skip AI-generated first message.</p>
        <br>

        <form method="POST" enctype="multipart/form-data">

            <label>Mautic Username:</label>
            <input type="text" name="username" required /><br><br>

            <label>Mautic Password:</label>
            <input type="password" name="password" required /><br><br>

            <label>Upload CSV File:</label>
            <input type="file" name="file" accept=".csv,.tsv,.txt" required /><br><br>

            <label>
                <input type="checkbox" name="skip_ai" />
                Upload WITHOUT AI-generated first messages
            </label>

            <br><br>
            <button type="submit">Process Upload</button>
        </form>
    </div>
</body>
</html>
"""

RESULT_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Copper Lead Importer - Result</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background: #faf7f2;
            display: flex;
            justify-content: center;
            padding-top: 40px;
        }
        .container {
            background: white;
            width: 520px;
            padding: 30px;
            border-radius: 14px;
            box-shadow: 0px 4px 20px rgba(0,0,0,0.1);
        }
        h2 {
            text-align: center;
            color: #d67f2f;
            margin-bottom: 10px;
        }
        .cat-box {
            text-align: center;
            margin-bottom: 20px;
        }
        .cat-box img {
            width: 120px;
            border-radius: 12px;
            box-shadow: 0px 2px 10px rgba(0,0,0,0.15);
        }
        pre {
            background: #f3eee7;
            padding: 12px;
            border-radius: 8px;
            max-height: 400px;
            overflow-y: auto;
            font-size: 13px;
            white-space: pre-wrap;
            word-wrap: break-word;
        }
        a {
            display: inline-block;
            margin-top: 10px;
            color: #d67f2f;
            text-decoration: none;
        }
        a:hover {
            text-decoration: underline;
        }
        .status-ok {
            color: #2f8f46;
            font-weight: bold;
            text-align: center;
            margin-bottom: 10px;
        }
        .status-error {
            color: #c0392b;
            font-weight: bold;
            text-align: center;
            margin-bottom: 10px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="cat-box">
            <img src="/static/copper.png" alt="Copper the Cat" />
        </div>

        <h2>Copper Lead Importer – Output</h2>

        {% if "Traceback" in output or "Error" in output or "Exception" in output %}
            <div class="status-error">Something went wrong while processing the file.</div>
        {% else %}
            <div class="status-ok">Leads processed. See detailed log below.</div>
        {% endif %}

        <pre>{{ output }}</pre>

        <a href="/">← Back to upload</a>
    </div>
</body>
</html>
"""

def is_mautic_admin(username, password):
    try:
        url = f"{MAUTIC_BASE_URL.rstrip('/')}/api/users/self"
        auth_str = f"{username}:{password}"
        auth_header = base64.b64encode(auth_str.encode("utf-8")).decode("utf-8")

        req = urllib.request.Request(
            url,
            headers={"Authorization": f"Basic {auth_header}"}
        )

        with urllib.request.urlopen(req) as resp:
            raw = resp.read().decode("utf-8")

        data = json.loads(raw)
        user = data.get("user") or data

        # 1) Check isAdmin field if present
        is_admin = False
        flag = user.get("isAdmin")
        if isinstance(flag, bool):
            is_admin = flag
        elif isinstance(flag, (int, str)):
            if str(flag).lower() in ("1", "true", "yes"):
                is_admin = True

        # 2) Check role field (can be string or dict)
        role = user.get("role")
        if not is_admin and isinstance(role, str):
            if "admin" in role.lower():
                is_admin = True
        if not is_admin and isinstance(role, dict):
            name = role.get("name", "")
            if isinstance(name, str) and "admin" in name.lower():
                is_admin = True

        # 3) Check roles list if present
        roles = user.get("roles")
        if not is_admin and isinstance(roles, list):
            for r in roles:
                if isinstance(r, str) and "admin" in r.lower():
                    is_admin = True
                elif isinstance(r, dict):
                    name = r.get("name", "")
                    if isinstance(name, str) and "admin" in name.lower():
                        is_admin = True

        print("DEBUG Mautic user info:", json.dumps(user, indent=2))
        print("DEBUG is_admin computed:", is_admin)

        return is_admin

    except urllib.error.HTTPError as e:
        # 401 typically = bad username/password
        print("DEBUG mautic admin check HTTPError:", e.code, e.read().decode("utf-8", "ignore"))
        return False
    except Exception as e:
        print("DEBUG mautic admin check Exception:", repr(e))
        return False


# -----------------------------
# FLASK APP
# -----------------------------

app = Flask(
    __name__,
    static_folder="/srv/mautic/static",  # absolute path to your static folder
    static_url_path="/static"            # URL prefix
)


@app.route("/", methods=["GET", "POST"])
def upload_page():
    if request.method == "GET":
        return UPLOAD_FORM_HTML

    # POST = credentials + file upload
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")

    if not username or not password:
        return "<h3>Username and password are required.</h3>", 400

    if not is_mautic_admin(username, password):
        return "<h3>❌ Access denied: Only Mautic admins can use this tool.</h3>", 403

    uploaded = request.files.get("file")
    if not uploaded:
        return "<h3>No file uploaded.</h3>", 400

    # Always save as leads.csv in the scripts folder
    uploaded.save(LEADS_CSV_PATH)

    # Base environment for the generator script
    env = os.environ.copy()
    # Let generate_and_push.py use its own CSV_PATH default
    env.pop("CSV_PATH", None)

    # Build command to run generator script
    skip_ai = "skip_ai" in request.form
    cmd = ["python3", GENERATE_SCRIPT]

    if skip_ai:
        print("[WEB] User selected: SKIP AI")
        cmd.append("--skip-ai")
    else:
        print("[WEB] AI ENABLED")

    try:
        result = subprocess.check_output(
            cmd,
            stderr=subprocess.STDOUT,
            env=env,
            universal_newlines=True,
        )
    except subprocess.CalledProcessError as e:
        result = e.output

    return render_template_string(RESULT_HTML, output=result)


if __name__ == "__main__":
    # For testing directly (not via gunicorn)
    app.run(host="0.0.0.0", port=8080)
