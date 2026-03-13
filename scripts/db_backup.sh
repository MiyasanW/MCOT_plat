#!/usr/bin/env bash
set -euo pipefail

# PostgreSQL backup script for MCOT Rental Platform
# - Reads DATABASE_URL from env or .env
# - Writes compressed dump to backups/postgres
# - Keeps only N days of backups
#
# Usage:
#   ./scripts/db_backup.sh
#   BACKUP_RETENTION_DAYS=14 ./scripts/db_backup.sh
#   DATABASE_URL=postgres://user:pass@localhost:5432/db ./scripts/db_backup.sh

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKUP_DIR="${BACKUP_DIR:-${PROJECT_DIR}/backups/postgres}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-14}"
TIMESTAMP="$(date +%Y%m%d-%H%M%S)"

if ! command -v pg_dump >/dev/null 2>&1; then
  echo "[FAIL] pg_dump not found"
  exit 1
fi

if [[ -z "${DATABASE_URL:-}" ]] && [[ -f "${PROJECT_DIR}/.env" ]]; then
  # shellcheck disable=SC2046
  export $(grep -E '^[A-Za-z_][A-Za-z0-9_]*=' "${PROJECT_DIR}/.env" | xargs)
fi

if [[ -z "${DATABASE_URL:-}" ]]; then
  echo "[FAIL] DATABASE_URL is not set"
  exit 1
fi

readarray -t DB_PARTS < <(python3 - <<'PY'
import os
from urllib.parse import urlparse

url = os.environ.get("DATABASE_URL", "").strip()
p = urlparse(url)
print(p.username or "")
print(p.password or "")
print(p.hostname or "localhost")
print(str(p.port or 5432))
print((p.path or "/").lstrip("/"))
PY
)

DB_USER="${DB_PARTS[0]}"
DB_PASS="${DB_PARTS[1]}"
DB_HOST="${DB_PARTS[2]}"
DB_PORT="${DB_PARTS[3]}"
DB_NAME="${DB_PARTS[4]}"

if [[ -z "${DB_USER}" || -z "${DB_NAME}" ]]; then
  echo "[FAIL] Invalid DATABASE_URL (missing user or db name)"
  exit 1
fi

mkdir -p "${BACKUP_DIR}"
BACKUP_FILE="${BACKUP_DIR}/${DB_NAME}_${TIMESTAMP}.sql.gz"

export PGPASSWORD="${DB_PASS}"
pg_dump \
  --host="${DB_HOST}" \
  --port="${DB_PORT}" \
  --username="${DB_USER}" \
  --format=plain \
  --no-owner \
  --no-privileges \
  "${DB_NAME}" | gzip -9 > "${BACKUP_FILE}"
unset PGPASSWORD

find "${BACKUP_DIR}" -type f -name '*.sql.gz' -mtime +"${RETENTION_DAYS}" -delete

LATEST_SIZE="$(du -h "${BACKUP_FILE}" | awk '{print $1}')"
echo "[OK] Backup created: ${BACKUP_FILE} (${LATEST_SIZE})"
echo "[OK] Retention policy: keep last ${RETENTION_DAYS} day(s)"
