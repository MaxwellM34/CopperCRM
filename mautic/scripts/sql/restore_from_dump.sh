#!/usr/bin/env bash
set -euo pipefail

# Restore a MariaDB dump into the local dockerized DB.
# Usage: ./scripts/sql/restore_from_dump.sh backup/remote_dump.sql

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
cd "${ROOT_DIR}"

DUMP_PATH="${1:-backup/remote_dump.sql}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.yml}"
DB_SERVICE="${DB_SERVICE:-db}"

if [[ ! -f "${DUMP_PATH}" ]]; then
  echo "SQL dump not found: ${DUMP_PATH}"
  exit 1
fi

echo "Starting MariaDB service (${DB_SERVICE})..."
docker compose -f "${COMPOSE_FILE}" up -d "${DB_SERVICE}"

DB_ROOT_PW="$(docker compose -f "${COMPOSE_FILE}" exec -T "${DB_SERVICE}" printenv MYSQL_ROOT_PASSWORD)"
DB_NAME="$(docker compose -f "${COMPOSE_FILE}" exec -T "${DB_SERVICE}" printenv MYSQL_DATABASE)"

if [[ -z "${DB_ROOT_PW}" || -z "${DB_NAME}" ]]; then
  echo "MYSQL_ROOT_PASSWORD or MYSQL_DATABASE not set in the container environment."
  exit 1
fi

echo "Dropping and recreating database ${DB_NAME}..."
docker compose -f "${COMPOSE_FILE}" exec -T "${DB_SERVICE}" sh -c "mysql -uroot -p\"${DB_ROOT_PW}\" -e 'DROP DATABASE IF EXISTS \\\`${DB_NAME}\\\`; CREATE DATABASE \\\`${DB_NAME}\\\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;'"

echo "Importing dump from ${DUMP_PATH} into ${DB_NAME}..."
docker compose -f "${COMPOSE_FILE}" exec -T "${DB_SERVICE}" sh -c "mysql -uroot -p\"${DB_ROOT_PW}\" ${DB_NAME}" < "${DUMP_PATH}"

echo "Restore complete."
