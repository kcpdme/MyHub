#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

if [[ ! -f .env ]]; then
  echo ".env not found. Create it first."
  exit 1
fi

read_env_value() {
  local key="$1"
  local line
  line="$(grep -E "^${key}=" .env | tail -n 1 || true)"
  if [[ -z "$line" ]]; then
    echo ""
    return
  fi

  # Strip KEY= prefix and optional surrounding quotes.
  line="${line#*=}"
  line="${line%\"}"
  line="${line#\"}"
  echo "$line"
}

TELEGRAM_BOT_TOKEN="$(read_env_value TELEGRAM_BOT_TOKEN)"
TELEGRAM_CHAT_ID="$(read_env_value TELEGRAM_CHAT_ID)"

MESSAGE="${1:-Test message from Personal Automation Hub}"

if [[ -n "${TELEGRAM_BOT_TOKEN:-}" && -n "${TELEGRAM_CHAT_ID:-}" ]]; then
  echo "Testing Telegram..."
  curl -sS -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
    -H "Content-Type: application/json" \
    -d "{\"chat_id\": \"${TELEGRAM_CHAT_ID}\", \"text\": \"${MESSAGE}\"}" | head -c 500 && echo
else
  echo "Skipping Telegram: set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env"
fi
