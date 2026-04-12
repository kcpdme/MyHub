#!/usr/bin/env bash
set -euo pipefail

TOKEN="${1:-${TELEGRAM_BOT_TOKEN:-}}"

if [[ -z "$TOKEN" ]]; then
  echo "Usage: TELEGRAM_BOT_TOKEN=<token> $0"
  echo "   or: $0 <token>"
  exit 1
fi

RAW="$(curl -sS "https://api.telegram.org/bot${TOKEN}/getUpdates")"

python3 - "$RAW" <<'PY'
import json
import sys

raw = (sys.argv[1] if len(sys.argv) > 1 else "").strip()
if not raw:
    print("No response. Check internet and token.")
    raise SystemExit(1)

try:
    data = json.loads(raw)
except Exception:
    print("Invalid JSON response:")
    print(raw)
    raise SystemExit(1)

if not data.get("ok"):
    print("Telegram API error:", data)
    raise SystemExit(1)

results = data.get("result", [])
if not results:
    print("No updates found. Send at least one message to your bot, then run again.")
    raise SystemExit(0)

seen = set()
for item in results:
    msg = item.get("message") or item.get("edited_message") or {}
    chat = msg.get("chat") or {}
    chat_id = chat.get("id")
    title = chat.get("title") or chat.get("username") or chat.get("first_name") or "unknown"
    if chat_id is not None and chat_id not in seen:
        seen.add(chat_id)
        print(f"chat_id={chat_id} name={title}")
PY
