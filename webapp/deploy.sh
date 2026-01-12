#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID="${PROJECT_ID:-crm-mvp-481223}"
NEXT_PUBLIC_API_BASE="${NEXT_PUBLIC_API_BASE:-}"
NEXT_PUBLIC_GOOGLE_CLIENT_ID="${NEXT_PUBLIC_GOOGLE_CLIENT_ID:-}"

gcloud builds submit \
  --project "$PROJECT_ID" \
  --config cloudbuild.webapp.yaml \
  --substitutions "_NEXT_PUBLIC_API_BASE=${NEXT_PUBLIC_API_BASE},_NEXT_PUBLIC_GOOGLE_CLIENT_ID=${NEXT_PUBLIC_GOOGLE_CLIENT_ID}"
