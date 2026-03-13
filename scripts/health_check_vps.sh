#!/usr/bin/env bash
set -euo pipefail

# Minimal health checks for VPS monitoring.
# Exit code 0 = healthy, non-zero = unhealthy.

BASE_URL="${BASE_URL:-https://mcotequipmentservices.mcot.net}"
SERVICE_NAME="${SERVICE_NAME:-gunicorn}"
DISK_THRESHOLD="${DISK_THRESHOLD:-90}"

failures=0

check_service() {
  if systemctl is-active --quiet "$SERVICE_NAME"; then
    echo "[OK] service ${SERVICE_NAME} is active"
  else
    echo "[FAIL] service ${SERVICE_NAME} is not active"
    failures=$((failures + 1))
  fi
}

check_http() {
  local code
  code="$(curl -sS -o /dev/null -w "%{http_code}" "$BASE_URL/")"
  if [[ "$code" =~ ^(200|301|302)$ ]]; then
    echo "[OK] HTTP ${BASE_URL}/ -> ${code}"
  else
    echo "[FAIL] HTTP ${BASE_URL}/ -> ${code}"
    failures=$((failures + 1))
  fi
}

check_disk() {
  local used
  used="$(df -P / | awk 'NR==2 {gsub("%","",$5); print $5}')"
  if [[ "$used" -lt "$DISK_THRESHOLD" ]]; then
    echo "[OK] disk usage ${used}% (< ${DISK_THRESHOLD}%)"
  else
    echo "[FAIL] disk usage ${used}% (>= ${DISK_THRESHOLD}%)"
    failures=$((failures + 1))
  fi
}

check_service
check_http
check_disk

if [[ "$failures" -gt 0 ]]; then
  echo "Health check failed: ${failures} issue(s)"
  exit 1
fi

echo "Health check passed"
