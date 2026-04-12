#!/usr/bin/env bash
set -euo pipefail

if [[ ! -f .env ]]; then
  echo ".env missing. Create and configure it first."
  exit 1
fi

echo "Building and starting Personal Automation Hub..."
docker compose up -d --build

echo "Done. App should be available on port 8000."
docker compose ps
