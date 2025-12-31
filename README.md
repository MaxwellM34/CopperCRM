# Copper CRM Stack
Stack overview covering the FastAPI backend in `api/`, the Next.js app in `webapp/`, and the Mautic add-on used for outbound analytics.

## Repo map
- `api/` FastAPI service with Tortoise ORM on Postgres, OpenAI-backed email generation, and Google OAuth or offline auth.
- `webapp/` Next.js 14 App Router front end for imports, lead views, and first-email workflows.
- `mautic/` Mautic 5 bundle kept for outbound sending and analytics. The `mautic/scripts/` folder is a parking lot of test and dev helpers that are inactive and saved as source material for future production code.

## API (FastAPI + Postgres)
- Runtime: Python 3.11+ (pyproject targets 3.14), FastAPI, Tortoise ORM, Aerich migrations. Entry point `api/main.py` with CORS enabled for localhost and the Cloud Run hosts.
- Config: `ENV=cloud` switches to Cloud SQL settings (`config/cloud.py`), otherwise `config/local.py` reads `.env`. Key vars: `PG_HOST`, `PG_PORT`, `PG_USER`, `PG_PASS`, `PG_DB`, `OPENAI_API_KEY`, optional `OPENAI_MODEL`, `GOOGLE_AUDIENCE`, `SERVER_URL`, `OFFLINE_MODE`, `OFFLINE_ADMIN_EMAIL`. Tortoise DSN is built into `Config.TORTOISE_ORM`.
- Run locally: `cd api`, install deps from `uv.lock` (for example `uv pip sync uv.lock`), then `python main.py` to start Uvicorn on port 8000.
- Auth: Google bearer token via `auth/google.py`; `OFFLINE_MODE=true` bypasses Google and provisions an offline admin from `OFFLINE_ADMIN_EMAIL`. Auth guard lives in `auth/authenticate.py` and is used by protected routes.
- Database shape (Tortoise models in `api/models/`):
  - `users`: email (unique), firstname, lastname, is_admin, disabled, timestamps.
  - `companies`: company_name plus size, address, contact channels, tech stack, funding fields; created_by/updated_by link to users.
  - `leads`: personal and work email (both unique), name, title, enrichment fields (seniority, departments, industries, profile_summary), gender with default `unknown_gender`, address/country/LinkedIn; FK to companies and created_by/updated_by users.
  - `first_email`: one-to-one with a lead; stores generated email text, OpenAI model, token counts, cost, approval flag, human edit snapshots.
  - `first_email_approvals`: one-to-one with a first_email; human, algorithm, and overall approval flags plus optional scoring dimensions.
  - `stages`: placeholder for pipeline stage keyed to a lead.
- Key routes:
  - `/auth/me` returns the authenticated user and doubles as a token check.
  - `/leads/import` accepts CSV uploads to upsert companies and leads (requires Work or Personal Email, First Name, Company). `/leads/display` lists lead cards with company and contact info.
  - `/first-emails/stats` reports pending counts and cost averages. `/first-emails/generate` creates first-touch emails for leads without one. `/first-emails/next` fetches the next email pending human review. `/first-emails/decision` records approved or rejected.
  - `/approval-stats/` reports how many generated emails still need a human decision.
  - `/users` supports creating users, listing, adminize/deadminize, and deletion (admin checks on privileged actions).
- OpenAI usage: `services/email_generation.py` builds lead context from lead and company data, calls Chat Completions (default `gpt-4o-mini`), stores token counts and estimated USD cost, and persists into `first_email`. Cost baselines can also come from historical CSV or JSON under `mautic/ai-leads/generated` and similar paths.
- Lifespan hooks: on startup the app writes `openai_tools.json` for tooling and backfills missing lead genders using `gender_guesser`.

## Webapp (Next.js)
- Stack: Next.js 14 with the App Router, Tailwind styling, React 18. Env vars: `NEXT_PUBLIC_API_BASE` (defaults to Cloud Run URL with localhost fallback), `NEXT_PUBLIC_GOOGLE_CLIENT_ID`. Tokens and API base live in localStorage via `src/lib/storage.ts`.
- Auth flow: landing page renders the Google Identity button. If the API is in offline mode, it skips Google and redirects straight into the app after calling `/auth/me`.
- Main screens:
  - `/crm` home tiles for imports, AI emails, leads, reports.
  - `/import` uploads CSVs to `/leads/import` and shows the JSON response.
  - `/emails` selects between generate and approve flows.
  - `/emails/generate` calls `/first-emails/stats` and `/first-emails/generate` to batch-create first emails with cost estimates.
  - `/emails/approve` pulls from `/first-emails/next` and `/approval-stats/` for swipe-style human decisions hitting `/first-emails/decision`.
  - `/leads` reads `/leads/display` and shows avatars, countries, and contact info.
- Run locally: `cd webapp && npm install && npm run dev` (port 3000). Point to a local API by setting `NEXT_PUBLIC_API_BASE=http://127.0.0.1:8000` or using the 'Use local' action on the generate page.

## Mautic add-on
- Purpose: shortcut for outbound sending and analytics with Mautic 5, separate from the FastAPI stack. Useful for email delivery, contact analytics, and as a reference while the core app matures.
- Scripts note: everything under `mautic/scripts/` is experimental or test-only, kept inactive and stored here until cleaned up and promoted into production-ready code.
