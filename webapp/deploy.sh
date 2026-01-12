#!/usr/bin/env bash
set -euo pipefail

SERVICE_NAME="${SERVICE_NAME:-crm-frontend-468831678336}"
REGION="${REGION:-us-central1}"
PROJECT_ID="${PROJECT_ID:-crm-mvp-481223}"
IMAGE="${IMAGE:-us-central1-docker.pkg.dev/${PROJECT_ID}/default/crm-frontend:latest}"

gcloud builds submit --tag "$IMAGE" .

gcloud run deploy "$SERVICE_NAME" \
  --image "$IMAGE" \
  --region "$REGION" \
  --project "$PROJECT_ID" \
  --allow-unauthenticated
