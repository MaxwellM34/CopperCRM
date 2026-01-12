#!/usr/bin/env bash
set -euo pipefail

SERVICE_NAME="${SERVICE_NAME:-crm-api-468831678336}"
REGION="${REGION:-us-central1}"
PROJECT_ID="${PROJECT_ID:-crm-mvp-481223}"

gcloud run deploy "$SERVICE_NAME" \
  --source . \
  --region "$REGION" \
  --project "$PROJECT_ID" \
  --allow-unauthenticated \
  --set-env-vars ENV=CLOUD
