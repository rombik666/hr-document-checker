#!/usr/bin/env bash

set -e

check_endpoint() {
  local url="$1"

  echo "[INFO] Checking ${url}"

  status_code=$(curl -s -o /dev/null -w "%{http_code}" "${url}")

  if [ "${status_code}" != "200" ]; then
    echo "[ERROR] ${url} returned ${status_code}"
    exit 1
  fi

  echo "[OK] ${url} returned 200"
}

check_endpoint "http://127.0.0.1:8000/api/v1/health"
check_endpoint "http://127.0.0.1:8000/api/v1/metrics"
check_endpoint "http://127.0.0.1:8000/api/v1/metrics/prometheus"
check_endpoint "http://127.0.0.1:8000/api/v1/rag/status"
check_endpoint "http://127.0.0.1:8000/api/v1/llm/status"
check_endpoint "http://127.0.0.1:8000/api/v1/admin/db/status"
check_endpoint "http://127.0.0.1:8000/api/v1/admin/storage/privacy-check"
check_endpoint "http://127.0.0.1:8000/web/"
check_endpoint "http://127.0.0.1:9090/-/ready"
check_endpoint "http://127.0.0.1:3000/api/health"
check_endpoint "http://127.0.0.1:5050"

echo ""
echo "[OK] Smoke test completed successfully."