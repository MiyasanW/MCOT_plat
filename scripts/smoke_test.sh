#!/usr/bin/env bash
set -euo pipefail

# Basic smoke test for quick post-deploy validation.
# Usage:
#   ./scripts/smoke_test.sh
#   BASE_URL=https://mcotequipmentservices.mcot.net ./scripts/smoke_test.sh

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"

check_http_ok() {
  local path="$1"
  local code
  code="$(curl -sS -o /dev/null -w "%{http_code}" "${BASE_URL}${path}")"
  if [[ "$code" =~ ^(200|301|302)$ ]]; then
    echo "[OK] ${path} -> ${code}"
  else
    echo "[FAIL] ${path} -> ${code}"
    return 1
  fi
}

echo "Running smoke test against ${BASE_URL}"
check_http_ok "/"
check_http_ok "/catalog/"
check_http_ok "/accounts/login/"
check_http_ok "/my-bookings/"

echo "Smoke test passed"
