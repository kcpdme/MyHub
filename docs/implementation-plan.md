# Personal Automation Hub - Implementation Plan

## 1. Goal
Build a self-hosted Personal Automation Hub that runs inside your mobile container (Droidspaces + VS Code Server), with:
- quick capture inbox (notes/links/ideas)
- task planner
- reminder engine
- channels: Telegram
- daily summary dashboard
- extensible automation jobs

## 2. Tech Stack
- Backend: FastAPI (Python 3.11+)
- DB: SQLite (single-file, low resource)
- ORM: SQLAlchemy
- Scheduler: APScheduler (background scheduler in app process)
- Frontend: Jinja2 templates + vanilla JS + CSS
- HTTP client for providers: httpx
- Env config: python-dotenv + pydantic-settings

## 3. Architecture

### 3.1 Core Modules
- `app/main.py`: FastAPI app bootstrap + scheduler lifecycle
- `app/config.py`: environment settings
- `app/database.py`: engine/session setup
- `app/models.py`: SQLAlchemy models
- `app/schemas.py`: Pydantic request/response schemas
- `app/services/`
  - `reminder_dispatcher.py`: route reminder to channel adapter
  - `channels/telegram_sender.py`: Telegram Bot API sender
  - `summary_service.py`: daily summary builder
- `app/routes/`
  - `api.py`: REST endpoints
  - `web.py`: dashboard pages
- `app/templates/` and `app/static/`: UI

### 3.2 Data Model (initial)
- `captures`: inbox entries (text, optional URL)
- `tasks`: title, status, due_date, priority
- `reminders`: message, remind_at, channel, target, status
- `delivery_logs`: per-attempt provider response
- `automation_jobs`: placeholder for recurring automations

### 3.3 Reminder Flow
1. User creates reminder with channel/target/time.
2. Scheduler checks due reminders every 30s.
3. Dispatcher sends reminder using selected channel adapter.
4. Log attempt and update status (`sent` / `failed`).

## 4. Reminder Channel Details

### 4.1 Telegram
- Input: bot token + chat ID
- API: `POST https://api.telegram.org/bot<TOKEN>/sendMessage`
- Good for immediate push notifications

## 5. Security Baseline
- Single-user auth token for API (`X-API-Key`)
- Secrets loaded from `.env`
- No secrets in repository
- Request validation for all endpoints

## 6. Delivery Phases

### Phase 1 (Now)
- Project scaffolding
- DB models + migrations via startup create
- CRUD APIs for captures/tasks/reminders
- scheduler + dispatch engine
- channel adapters (Telegram)
- basic dashboard UI

### Phase 2
- recurring reminders and routines
- daily digest job (scheduled)
- better filtering/search and statuses

### Phase 3
- PWA polish + mobile UX improvements
- backup/export/import
- plugin-style automation job runners

## 7. API Endpoints (v1)
- `GET /health`
- `GET /api/captures`, `POST /api/captures`
- `GET /api/tasks`, `POST /api/tasks`, `PATCH /api/tasks/{id}`
- `GET /api/reminders`, `POST /api/reminders`
- `POST /api/reminders/{id}/send-now`
- `GET /api/summary/today`

## 8. Configuration (`.env`)
- `APP_NAME`
- `APP_HOST`, `APP_PORT`
- `APP_API_KEY`
- `DATABASE_URL`
- `SCHEDULER_POLL_SECONDS`
- `TELEGRAM_BOT_TOKEN`

## 9. Runbook
1. Create venv and install requirements
2. Copy `.env.example` to `.env` and fill provider credentials
3. Start app via Uvicorn
4. Open dashboard in browser
5. Add a reminder and test send on each channel

## 10. Success Criteria
- Can create a reminder from UI
- reminder auto-sends when due
- provider response captured in logs
- dashboard shows today summary and pending reminders
- all works on low-resource mobile container
