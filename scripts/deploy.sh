#!/usr/bin/env bash
# deploy.sh — Deploy / update Personal Automation Hub on the server.
#
# Usage:
#   bash scripts/deploy.sh
#
# What it does:
#   1. Checks .env exists
#   2. Pulls latest code (if inside a git repo)
#   3. Builds and starts/restarts Docker containers
#   4. Shows live logs (Ctrl+C to stop watching, containers keep running)

set -euo pipefail

echo ""
echo "╔══════════════════════════════════════════╗"
echo "║     AutoHub Deployment Script            ║"
echo "╚══════════════════════════════════════════╝"
echo ""

# ── Preflight checks ──────────────────────────────────────────────────────────
if [[ ! -f .env ]]; then
  echo "✗ ERROR: .env not found."
  echo "  Run:  cp .env.example .env  then fill in your values."
  exit 1
fi

# Check required vars are set
for var in APP_API_KEY POSTGRES_PASSWORD TELEGRAM_BOT_TOKEN TELEGRAM_CHAT_ID NOTES_ENCRYPTION_KEY; do
  value=$(grep -E "^${var}=" .env | cut -d= -f2- | tr -d '"' | tr -d "'" || true)
  if [[ -z "$value" || "$value" == "change-me"* ]]; then
    echo "✗ ERROR: ${var} is not set in .env"
    exit 1
  fi
done
echo "✓ .env looks good"

# ── Pull latest code ──────────────────────────────────────────────────────────
if [[ -d .git ]]; then
  echo "✓ Pulling latest code..."
  git pull --ff-only
fi

# ── Build and start ───────────────────────────────────────────────────────────
echo "✓ Building and starting containers..."
docker compose up -d --build --remove-orphans

echo ""
echo "✓ Containers started. Services:"
docker compose ps

echo ""
echo "✓ Watching logs (Ctrl+C to stop — containers keep running):"
echo "──────────────────────────────────────────────────────────"
docker compose logs -f --tail=50
