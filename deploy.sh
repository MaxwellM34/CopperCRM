#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${ENV_FILE:-$ROOT_DIR/.env}"

if [[ -f "$ENV_FILE" ]]; then
  set -a
  # shellcheck disable=SC1090
  . "$ENV_FILE"
  set +a
fi

(
  cd "$ROOT_DIR/api"
  bash deploy.sh
)

(
  cd "$ROOT_DIR/webapp"
  bash deploy.sh
)

(
  cd "$ROOT_DIR/extension"
  bash deploy.sh
)
