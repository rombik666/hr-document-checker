#!/usr/bin/env bash

set -e

echo "Warning!"
echo "This script will stop containers and remove Docker volumes."
echo "PostgreSQL, Prometheus and Grafana Docker volumes will be removed."
echo "Local data/ and backups/ directories will NOT be removed."
echo ""

read -r -p "Type YES to continue: " confirmation

if [ "$confirmation" != "YES" ]; then
  echo "Reset cancelled."
  exit 0
fi

docker compose down -v --remove-orphans

echo "[OK] Docker environment has been reset."