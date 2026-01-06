## Copper CRM LinkedIn Extension MVP

### Backend (FastAPI + Tortoise)

1. Install backend dependencies:

```bash
cd api
pip install -e .
```

Or use your preferred workflow (`uv pip install`, `poetry`, etc.) with `api/pyproject.toml`.

2. Configure environment variables (example `.env`):

```env
GOOGLE_CLIENT_ID=your-google-oauth-client-id.apps.googleusercontent.com
THREADS_ENCRYPTION_KEY=base64-url-safe-32-byte-key
PG_HOST=localhost
PG_PORT=5432
PG_USER=postgres
PG_PASS=password
PG_DB=crm_local
```

Generate a Fernet key:

```bash
python - <<'PY'
from cryptography.fernet import Fernet
print(Fernet.generate_key().decode())
PY
```

3. Run migrations (Aerich):

```bash
cd api
aerich upgrade
```

4. Start the API:

```bash
cd api
uvicorn main:app --reload
```

5. Grant extension permission to a user:

```sql
UPDATE users SET can_use_extension = true WHERE email = 'you@example.com';
```

### Chrome Extension (Manifest V3)

1. Open Chrome → Extensions → Enable Developer Mode.
2. Click **Load unpacked** and select the `extension/` folder.
3. Open the extension **Options** page and set:
   - API Base URL (e.g., `http://localhost:8000`)
   - Google OAuth Client ID
4. Navigate to LinkedIn:
   - Profile page (`linkedin.com/in/*`) → click **Add To Copper**
   - Messaging page (`linkedin.com/messaging/*`) → click **Save Conversation**

### Manual Test Checklist

1. Open a LinkedIn profile → sidebar shows preview → click **Add To Copper**.
2. Verify lead updated and avatar fetch via `GET /leads/{id}/avatar`.
3. Open a LinkedIn message thread → sidebar shows **Save Conversation** → click.
4. Verify thread data stored encrypted and read via `GET /threads/{thread_id}`.
