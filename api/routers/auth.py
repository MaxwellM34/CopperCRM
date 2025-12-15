from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from config import Config

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/login", include_in_schema=False)
async def login_page() -> HTMLResponse:
    client_id = getattr(Config, "GOOGLE_AUDIENCE", None)
    client_id_js = (client_id or "").replace("\\", "\\\\").replace('"', '\\"')

    html = f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>CRM Auth Login</title>
    <script src="https://accounts.google.com/gsi/client" async defer></script>
    <style>
      body {{ font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif; margin: 24px; max-width: 900px; }}
      .row {{ display: flex; gap: 12px; align-items: center; flex-wrap: wrap; }}
      textarea {{ width: 100%; min-height: 160px; font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; }}
      button {{ padding: 8px 12px; cursor: pointer; }}
      code {{ font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; }}
      .muted {{ color: #555; }}
      .warn {{ color: #b45309; }}
    </style>
  </head>
  <body>
    <h1>Login</h1>
    <p class="muted">Sign in with Google to get an ID token for API calls.</p>
    <p class="muted">Swagger: open <code>/docs</code>, click Authorize, and paste the raw token only (no <code>Bearer</code> prefix).</p>
    <p class="muted">Origin: <code id="origin"></code> &nbsp;|&nbsp; Client ID: <code id="clientId"></code></p>
    <p class="muted">If Google shows <code>origin_mismatch</code>, add the origin above to the OAuth Client's <code>Authorized JavaScript origins</code>.</p>

    <div class="row">
      <div id="g_id_signin"></div>
      <button id="copyBtn" type="button" disabled>Copy token</button>
      <button id="clearBtn" type="button" disabled>Clear</button>
    </div>

    <p id="status" class="muted"></p>

    <h3>Token</h3>
    <textarea id="token" placeholder="Token will appear here..." readonly></textarea>

    <script>
      const CLIENT_ID = "{client_id_js}";

      const tokenEl = document.getElementById("token");
      const copyBtn = document.getElementById("copyBtn");
      const clearBtn = document.getElementById("clearBtn");
      const statusEl = document.getElementById("status");

      function setStatus(text, cls) {{
        statusEl.textContent = text || "";
        statusEl.className = cls || "muted";
      }}

      function setToken(token) {{
        tokenEl.value = token || "";
        const has = Boolean(token);
        copyBtn.disabled = !has;
        clearBtn.disabled = !has;
      }}

      function handleCredentialResponse(response) {{
        setToken(response.credential);
        setStatus("Token received. Use it as: Authorization: Bearer <token>", "muted");
      }}

      copyBtn.addEventListener("click", async () => {{
        try {{
          await navigator.clipboard.writeText(tokenEl.value);
          setStatus("Copied to clipboard.", "muted");
        }} catch (e) {{
          setStatus("Copy failed (browser permissions). Select + copy manually.", "warn");
        }}
      }});

      clearBtn.addEventListener("click", () => {{
        setToken("");
        setStatus("", "muted");
      }});

      window.addEventListener("load", () => {{
        document.getElementById("origin").textContent = window.location.origin;
        document.getElementById("clientId").textContent = CLIENT_ID || "(missing)";

        if (!CLIENT_ID) {{
          setStatus("Missing GOOGLE_AUDIENCE (Google OAuth client id). Set it in .env and restart the API.", "warn");
          return;
        }}

        google.accounts.id.initialize({{
          client_id: CLIENT_ID,
          callback: handleCredentialResponse,
        }});

        google.accounts.id.renderButton(
          document.getElementById("g_id_signin"),
          {{ theme: "outline", size: "large", text: "signin_with", shape: "pill" }}
        );
      }});
    </script>
  </body>
</html>
"""
    return HTMLResponse(content=html)

