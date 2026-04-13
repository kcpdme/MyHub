# Personal Automation Hub

Self-hosted automation hub for mobile container usage with:
- quick captures
- task tracking
- scheduled reminders
- recurring reminders
- reminder channels: Telegram
- daily summary dashboard + optional auto-send digest
- encrypted notes at rest
- Telegram bot command interface (allowlist protected)

## Run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Open `http://localhost:8000` in browser.

## Channel setup

### Telegram
1. Create a bot with BotFather.
2. Put bot token into `TELEGRAM_BOT_TOKEN`.
3. Use your Telegram chat id as reminder `target`.

Quick way to fetch your chat id:

```bash
./scripts/get_telegram_chat_id.sh <TELEGRAM_BOT_TOKEN>
```

If it says no updates found, send one message to your bot and run again.

## Telegram Bot Commands (Single App)

Bot worker runs inside the same app process when `TELEGRAM_BOT_POLLING_ENABLED=true`.

Commands:
- `/id`
- `/help`
- `/note add <content>`
- `/note list`
- `/task add <title>`
- `/task list`
- `/capture <text>`
- `/remind <minutes> <message>`

Allowlist protection:
- Add your Telegram user ID to allowlist via API:

```bash
KEY=$(grep '^APP_API_KEY=' .env | cut -d= -f2-)
curl -H "X-API-Key: $KEY" -H "Content-Type: application/json" \
	-d '{"telegram_user_id":"YOUR_USER_ID","display_name":"self"}' \
	http://127.0.0.1:8000/api/telegram/allowlist
```

## Quick Telegram test

Set this value in `.env`:
- `TELEGRAM_CHAT_ID`

Then run:

```bash
./scripts/test_channels.sh "hello from setup test"
```

## Daily Summary Auto-Send
Configure in `.env`:
- `DAILY_SUMMARY_ENABLED=true`
- `DAILY_SUMMARY_TIME_UTC=19:00` (UTC time)
- `DAILY_SUMMARY_CHANNEL=telegram`
- `DAILY_SUMMARY_TARGET=<chat_id>`

The app checks every minute and sends the digest once per day after a successful delivery.

## API key
All `/api/*` endpoints require header:
- `X-API-Key: <APP_API_KEY>`

Auth is database-backed:
- On startup, `APP_API_KEY` from `.env` is inserted into `api_keys` table if missing.
- Requests validate against active hashed keys in DB.
- You can create additional keys via `POST /api/auth/keys` and deactivate with `POST /api/auth/keys/{id}/deactivate`.

UI stores API key in browser local storage for convenience.

## Notes
- Database is SQLite file `automation_hub.db`.
- Reminder scheduler checks due reminders every `SCHEDULER_POLL_SECONDS`.
- Recurring reminders require `is_recurring=true` and `recurrence_minutes`.

## One-App Packaging (Phone -> DigitalOcean)

This project can run as one single containerized app containing:
- web UI
- API
- scheduler
- Telegram bot polling worker

### Local/Droplet Docker run

```bash
chmod +x scripts/deploy_do.sh
./scripts/deploy_do.sh
```

Or manually:

```bash
docker compose up -d --build
```

Data persistence:
- SQLite stored at `./data/automation_hub.db` via docker volume mapping.

## Media Storage (Telegram Inbox Files)

By default, inbox media/files are cached on local disk under `./media`.

You can switch to Cloudflare R2 (recommended for durability):

1. Set these values in `.env`:
	- `MEDIA_STORAGE_BACKEND=r2`
	- `MEDIA_R2_ACCOUNT_ID=<your_account_id>`
	- `MEDIA_R2_BUCKET=<bucket_name>`
	- `MEDIA_R2_ACCESS_KEY_ID=<access_key_id>`
	- `MEDIA_R2_SECRET_ACCESS_KEY=<secret_key>`
2. Rebuild/restart:

```bash
docker compose up -d --build
```

Behavior:
- Reads local cache first for speed.
- If not found locally, checks R2.
- If not found in R2, downloads from Telegram, serves it, and stores to local cache + R2.
