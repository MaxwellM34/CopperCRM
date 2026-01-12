#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DIST_DIR="$ROOT_DIR/dist"
ZIP_NAME="copper-extension.zip"

mkdir -p "$DIST_DIR"

(
  cd "$ROOT_DIR"
  rm -f "$DIST_DIR/$ZIP_NAME"
  zip -r "$DIST_DIR/$ZIP_NAME" . \
    -x "dist/*" \
    -x ".git/*" \
    -x "*.zip"
)

if [[ -n "${EXTENSION_BUCKET:-}" ]]; then
  gsutil cp "$DIST_DIR/$ZIP_NAME" "gs://$EXTENSION_BUCKET/$ZIP_NAME"
else
  echo "EXTENSION_BUCKET not set; built $DIST_DIR/$ZIP_NAME only."
fi
