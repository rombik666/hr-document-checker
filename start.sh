#!/usr/bin/env bash

set -e

echo "[INFO] Checking Docker..."

if ! command -v docker >/dev/null 2>&1; then
  echo "[ERROR] Docker is not installed."
  exit 1
fi

if ! docker info >/dev/null 2>&1; then
  echo "[ERROR] Docker is installed, but Docker is not running."
  exit 1
fi

echo "[OK] Docker is available."

if [ ! -f ".env" ] && [ -f ".env.example" ]; then
  cp .env.example .env
  echo "[OK] Created .env from .env.example."
fi

mkdir -p data
mkdir -p data/samples
mkdir -p data/knowledge_base
mkdir -p data/index
mkdir -p backups

if command -v python >/dev/null 2>&1 && [ -f "scripts/create_demo_samples.py" ]; then
  python scripts/create_demo_samples.py || echo "[WARN] Demo samples were not created."
fi

echo "[INFO] Starting Docker Compose..."
docker compose up -d --build

echo ""
echo "System is running."
echo ""
echo "Web UI:             http://127.0.0.1:8000/web/"
echo "Swagger API:        http://127.0.0.1:8000/docs"
echo "Health check:       http://127.0.0.1:8000/api/v1/health"
echo "JSON metrics:       http://127.0.0.1:8000/api/v1/metrics"
echo "RAG status:         http://127.0.0.1:8000/api/v1/rag/status"
echo "Prometheus:         http://127.0.0.1:9090"
echo "Grafana:            http://127.0.0.1:3000"
echo ""
echo "Grafana login:      admin"
echo "Grafana password:   admin"
echo ""
echo "Stop system:        ./stop.sh"
echo "Reset environment:  ./reset.sh"