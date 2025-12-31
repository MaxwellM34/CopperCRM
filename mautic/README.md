# KrakenSense Mautic Stack
Containerized CRM environment for Kraken Sense built on Mautic 5, MariaDB, and Python AI helpers for lead enrichment, outreach, and cleanup. All custom scripts are volume-mounted so host edits reflect immediately inside the running containers.

## Repository Map
- `docker-compose.yml` - Mautic 5 + MariaDB services and volume mounts.
- `scripts/` - operational tooling:
  - `ai-leads/` - OpenAI-powered lead ingestion (`generate_and_push.py`), CSV web uploader, approval API, and email scoring/editing helpers.
  - `sql/` - lead cleanup SQL and runner script.
  - `rotate_senders.sh` - rotates outbound senders for `mautic:emails:send`.
- `cron/` - version-controlled cron entries (`mautic-cron.txt`) and installer.
- `backup/backup_mautic.sh` - full backup and optional rclone upload.
- `static/` - assets used by the approval/uploader apps.

## Setup Repo
1) Clone to the expected host path (cron/scripts assume `/srv/mautic`):
   `git clone <repo-url> /srv/mautic && cd /srv/mautic`
2) Create `.env` in the project root using the template below.
3) Ensure `uploads/` exists for mounted uploads: `mkdir -p uploads`.
4) Bring up the stack: `docker compose up -d`.
5) Install cron jobs on the host: `./cron/install_cron.sh`.

## Prerequisites
- Docker and Docker Compose v2 on the host.
- Host checkout at `/srv/mautic` (cron and scripts assume this path).
- `.env` file in the project root with the variables below.

## Configuration (.env template)
```
# MariaDB
MYSQL_ROOT_PASSWORD=changeme-root
MYSQL_DATABASE=mautic
MYSQL_USER=mauticuser
MYSQL_PASSWORD=changeme-db-user

# Mautic container
MAUTIC_DB_HOST=db
MAUTIC_DB_PORT=3306
MAUTIC_DB_DATABASE=${MYSQL_DATABASE}
MAUTIC_DB_USER=${MYSQL_USER}
MAUTIC_DB_PASSWORD=${MYSQL_PASSWORD}
MAUTIC_RUN_CRON_JOBS=false
MAUTIC_INSTALLER=true
PHP_MEMORY_LIMIT=2G
TZ=America/Toronto

# Mautic API / UI auth for scripts
MAUTIC_BASE_URL=http://localhost
MAUTIC_USERNAME=your_admin_user
MAUTIC_PASSWORD=your_admin_pass

# AI
OPENAI_API_KEY=sk-...
# Optional: override defaults for generator
PROMPT_ID=kraken_sdr_v2
CSV_PATH=leads.csv
```

## Run the Stack
1) Start services: `docker compose up -d`
2) Stop services: `docker compose down`
3) Mautic UI: http://localhost (adjust if published on a server).

Volumes (inside containers):
- `/var/www/html` (mautic_data)
- `/var/lib/mysql` (db_data)
- Custom mounts: `/opt/mautic/scripts`, `/opt/mautic/cron`, `/opt/mautic/backup`, `/opt/mautic/uploads`

## Restore Existing DB + Config Locally
Mirror the current online MariaDB into the local Docker stack and keep PHP config in sync.
1) Export the remote DB (replace host/user/db): `mysqldump -h <remote-host> -u <user> -p'<password>' --single-transaction --routines --triggers <db> > backup/remote_dump.sql`
2) Copy your current Mautic PHP config so the container uses the same settings (typically `config/local.php`): `docker cp <remote-mautic-container>:/var/www/html/config/local.php backup/local.php` (also grab any custom assets/themes you need).
3) Ensure `.env` here matches those DB credentials and `MAUTIC_INSTALLER=false` so the installer is skipped.
4) Import the dump into the local MariaDB container: `docker compose up -d db` then `./scripts/sql/restore_from_dump.sh backup/remote_dump.sql` (drops/recreates the DB before loading).
5) Start the app: `docker compose up -d mautic`.
6) Apply the saved PHP config: `docker cp backup/local.php mautic-app:/var/www/html/config/local.php` then `docker compose restart mautic` so Mautic reads it.

## AI Lead Workflow
- Primary script: `scripts/ai-leads/generate_and_push.py`
  - Reads `leads.csv` (default path can be overridden with `CSV_PATH` env).
  - Fetches optional snippets from company sites, crafts outreach via OpenAI, and creates/updates contacts in Mautic.
  - Flags: `--skip-ai` to bypass generation and just push contacts.
  - Run inside the container:
    `docker exec -it mautic-app python3 /opt/mautic/scripts/ai-leads/generate_and_push.py`
- Prompts live in `scripts/ai-leads/prompts/` and are selected via `PROMPT_ID`.

### CSV Web Uploader
- App: `scripts/ai-leads/web_uploader.py` (Flask, port 8080).
- Lets an authenticated Mautic user upload `leads.csv` and trigger the generator (optionally `--skip-ai`).
- Example run inside the container:
  `docker exec -it mautic-app python3 /opt/mautic/scripts/ai-leads/web_uploader.py`

### Approval / Scoring Helpers
- `approval_app.py` exposes `/api/next` and related endpoints against `copper_emails.db` for human approval flows; serves assets from `static/`.
- `email_editor.py`, `email_scoring.py`, `archive_*` helpers support refining and archiving generated messages.
- `mautic_sync.py` handles pushes to Mautic for the above tools.
- `inbound_approval_app.py` (Flask, port 5003) reviews inbound replies stored in `inbox_emails` (see fetch scripts below). It shows an AI thread summary and an editable AI-suggested reply. Approve/Reject updates Mautic contact custom fields `ai_email_2` (textarea) and `email_2_approval` (approved/rejected). If the reply is classified as “not interested,” a banner appears with the option to delete the contact instead.

## Cron Jobs
- Source file: `cron/mautic-cron.txt`
- Install into host crontab:
  `./cron/install_cron.sh`
- Tasks included:
  - Segment and campaign updates/triggers every minute.
  - Email sending via sender rotator (`scripts/rotate_senders.sh`).
  - IMAP fetch for bounces/replies.
  - Daily backup at 08:00.
  - Lead cleanup SQL runner every minute.

## Sender Rotation
- Edit `SENDERS` in `scripts/rotate_senders.sh` with `FROM_NAME|FROM_EMAIL|MAILER_DSN` entries.
- Script tracks the last sender in `scripts/rotator_state` and cycles through on each cron invocation.
- Cron calls `mautic:emails:send` with a 5-message batch and 300/day max.

## Backups
- Script: `backup/backup_mautic.sh`
- Captures: MariaDB dump, Mautic application files, Docker volumes (`mautic_data`, `mautic_db_data`), host `/opt/mautic` and `/srv/mautic`, crontab, rclone config, SSL/nginx if present, and Mautic config files.
- Archives to `/srv/full_backup_<timestamp>.tar.gz` and optionally uploads to Google Drive folder `mautic_backups` via `rclone`.
- Cron entry runs daily at 08:00; can be invoked manually:
  `/srv/mautic/backup/backup_mautic.sh`

## Lead Cleanup SQL
- Location: `scripts/sql/`
  - `01_inspect_leads.sql`, `02_cleanup_junk_leads.sql`, `03_cleanup_orphan_references.sql`
  - Runner: `run_lead_cleanup.sh` (cron executes it; uses the MariaDB root password from the script).
- Logs to `/var/log/mautic_lead_cleanup.log`.

## Inbound Reply Capture & Debug
- `reply_receiver.py` — webhook for Mautic “contact replied” events; looks up the latest IMAP message, parses it, and stores in `email_replies`.
- `fetch_latest_email.py` — CLI: fetch newest message from a sender via IMAP and print JSON.
- `fetch_and_store_email.py` — CLI: fetch newest message from a sender, parse, store in `inbox_emails` (also stores replied-to message in metadata).
- `debug_webhook.py` — echo endpoint at `/debug/webhook` (port 5002) to inspect payloads; `?check_imap=1` tests IMAP connectivity.

### Inbound Review Flow
1) Fetch replies into SQLite with `fetch_and_store_email.py sender@example.com` (uses IMAP env vars).
2) Run `inbound_approval_app.py` (127.0.0.1:5003):
   - Left: editable AI-suggested reply.
   - Right: contact info (from `emails` table), thread summary, and original message.
   - “Not interested” banner shown if AI classifies disinterest; you can delete the contact or send a reply anyway.
3) Approve/Reject: updates the Mautic contact with `ai_email_2` (suggested/edited reply) and `email_2_approval` (approved/rejected). Delete: removes the contact in Mautic by email.

## Deployment Notes
- Keep the repo at `/srv/mautic` to match cron paths.
- Custom uploads live in `uploads/` (mounted into `/opt/mautic/uploads`).
- Logs created by scripts are ignored via `.gitignore` (`*.log`, `uploader.log`, generated CSVs`).

## Google Cloud Build
- Config: `mautic/cloudbuild.yaml` builds the custom Mautic image via `mautic/Dockerfile` (scripts/cron baked in) and pushes to Artifact Registry.
- Prereqs: enable Cloud Build + Artifact Registry, create an Artifact Registry repo (default `_REPO=mautic`) in your region (`_REGION=us-central1`), and authenticate `gcloud`.
- Build/push example: `gcloud builds submit mautic --config mautic/cloudbuild.yaml --substitutions=_REGION=us-central1,_REPO=mautic,_TAG=$(git rev-parse --short HEAD)` → image `us-central1-docker.pkg.dev/$PROJECT_ID/mautic/mautic:<tag>`.
- To run with that image locally or in prod, set `MAUTIC_IMAGE` to the pushed image before `docker compose up` (compose now honors the env override).
- For Cloud Run/GKE, pair the image with a managed DB (Cloud SQL for MariaDB) and set matching `MAUTIC_DB_*` env vars; seed the DB via the import steps above or a Cloud SQL import job.
