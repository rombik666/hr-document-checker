#!/usr/bin/env bash

set -e

echo "[INFO] Stopping Docker Compose environment..."

docker compose down

echo "[OK] System stopped."