#!/usr/bin/env bash
set -euo pipefail

# PostgreSQL restore script for MCOT Rental Platform.
# Safety-first defaults:
# - requires explicit confirmation: CONFIRM_RESTORE=YES
# - can run dry-run mode: DRY_RUN=1
# - auto backup current DB before restore (default ON)
#
# Usage:
#   CONFIRM_RESTORE=YES ./scripts/db_restore.sh backups/postgres/file.sql.gz
#   CONFIRM_RESTORE=YES ./scripts/db_restore.sh
#   DRY_RUN=1 ./scripts/db_restore.sh backups/postgres/file.sql.gz

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKUP_DIR="${BACKUP_DIR:-${PROJECT_DIR}/backups/postgres}"
CONFIRM_RESTORE="${CONFIRM_RESTORE:-NO}"
DRY_RUN="${DRY_RUN:-0}"
AUTO_BACKUP_BEFORE_RESTORE="${AUTO_BACKUP_BEFORE_RESTORE:-1}"

if ! command -v psql >/dev/null 2>&1; then
  echo "[FAIL] psql not found"
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

INPUT_FILE="${1:-}"
if [[ -z "${INPUT_FILE}" ]]; then
  INPUT_FILE="$(ls -1t "${BACKUP_DIR}"/*.sql.gz 2>/dev/null | head -n 1 || true)"
fi

if [[ -z "${INPUT_FILE}" || ! -f "${INPUT_FILE}" ]]; then
  echo "[FAIL] Backup file not found"
  echo "Usage: CONFIRM_RESTORE=YES ./scripts/db_restore.sh <backup_file.sql.gz>"
  exit 1
fi

echo "Target DB     : ${DB_NAME}@${DB_HOST}:${DB_PORT}"
echo "Backup source : ${INPUT_FILE}"

echo "This operation will overwrite data in target database."
if [[ "${CONFIRM_RESTORE}" != "YES" ]]; then
  echo "[ABORT] Set CONFIRM_RESTORE=YES to continue"
  exit 1
fi

if [[ "${DRY_RUN}" == "1" ]]; then
  echo "[DRY_RUN] Restore command is valid and ready"
  exit 0
fi

if [[ "${AUTO_BACKUP_BEFORE_RESTORE}" == "1" ]]; then
  echo "[INFO] Creating safety backup before restore"
  "${PROJECT_DIR}/scripts/db_backup.sh"
fi

export PGPASSWORD="${DB_PASS}"
gzip -dc "${INPUT_FILE}" | psql \
  --host="${DB_HOST}" \
  --port="${DB_PORT}" \
  --username="${DB_USER}" \
  --dbname="${DB_NAME}" \
  --set ON_ERROR_STOP=1
unset PGPASSWORD

echo "[OK] Restore completed"
