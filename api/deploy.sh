#!/usr/bin/env bash
set -euo pipefail

SERVICE_NAME="${SERVICE_NAME:-crm-api-468831678336}"
REGION="${REGION:-us-central1}"
PROJECT_ID="${PROJECT_ID:-crm-mvp-481223}"

required_vars=(PG_GCP_PATH PG_USER PG_PASS PG_DB GOOGLE_AUDIENCE SERVER_URL)
missing_vars=()

for var in "${required_vars[@]}"; do
  if [[ -z "${!var:-}" ]]; then
    missing_vars+=("$var")
  fi
done

if (( ${#missing_vars[@]} > 0 )); then
  echo "Missing required env vars: ${missing_vars[*]}"
  echo "Set them in .env or your shell before deploying."
  exit 1
fi

env_vars=(
  "ENV=CLOUD"
  "PG_GCP_PATH=${PG_GCP_PATH}"
  "PG_PORT=${PG_PORT:-5432}"
  "PG_USER=${PG_USER}"
  "PG_PASS=${PG_PASS}"
  "PG_DB=${PG_DB}"
  "GOOGLE_AUDIENCE=${GOOGLE_AUDIENCE}"
  "SERVER_URL=${SERVER_URL}"
)

if [[ -n "${PG_HOST:-}" ]]; then
  env_vars+=("PG_HOST=${PG_HOST}")
fi
if [[ -n "${EXTENSION_AUTO_UPDATE:-}" ]]; then
  env_vars+=("EXTENSION_AUTO_UPDATE=${EXTENSION_AUTO_UPDATE}")
fi

gcloud run deploy "$SERVICE_NAME" \
  --source . \
  --region "$REGION" \
  --project "$PROJECT_ID" \
  --allow-unauthenticated \
  --set-env-vars "$(IFS=,; echo "${env_vars[*]}")"
