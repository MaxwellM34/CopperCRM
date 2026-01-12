#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROJECT_ID="${PROJECT_ID:-crm-mvp-481223}"
NEXT_PUBLIC_API_BASE="${NEXT_PUBLIC_API_BASE:-}"
NEXT_PUBLIC_GOOGLE_CLIENT_ID="${NEXT_PUBLIC_GOOGLE_CLIENT_ID:-}"

gcloud builds submit \
  "$ROOT_DIR" \
  --project "$PROJECT_ID" \
  --config "$ROOT_DIR/webapp/cloudbuild.webapp.yaml" \
  --substitutions "_NEXT_PUBLIC_API_BASE=${NEXT_PUBLIC_API_BASE},_NEXT_PUBLIC_GOOGLE_CLIENT_ID=${NEXT_PUBLIC_GOOGLE_CLIENT_ID}"
