from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Project root = parent of this file's parent (app/config.py → workspace/)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_DB = f"sqlite:///{_PROJECT_ROOT / 'automation_hub.db'}"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Personal Automation Hub"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    app_api_key: str = "change-me"
    app_version: str = "2.0.0"

    database_url: str = _DEFAULT_DB
    scheduler_poll_seconds: int = 30
    daily_summary_enabled: bool = False
    daily_summary_time_utc: str = "19:00"
    daily_summary_channel: str = "telegram"
    daily_summary_target: str = ""

    # Postgres password — used by docker-compose to spin up the DB service.
    # The DATABASE_URL in docker-compose overrides the one here automatically.
    postgres_password: str = "changeme_strong_password"

    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    telegram_bot_polling_enabled: bool = True
    telegram_bot_poll_timeout_seconds: int = 20
    # If True, polling mode discards old queued Telegram updates on startup so
    # commands sent before a restart are not replayed out of context.
    telegram_poll_drop_pending_on_start: bool = True
    # If set, the bot registers a webhook instead of using long-polling.
    # Must be a publicly reachable HTTPS URL, e.g. https://yourdomain.com/telegram/webhook
    telegram_webhook_url: str = ""
    # Random secret token used to validate incoming webhook requests from Telegram.
    # Generate with: python -c "import secrets; print(secrets.token_hex(32))"
    telegram_webhook_secret: str = ""

    # Public HTTPS URL of the Telegram Mini App, e.g. https://hub.kcpd.top/miniapp
    # Used to generate the "Open Dashboard" button in bot messages and set the menu button.
    # If empty, the server auto-detects base URL (works fine behind Cloudflare tunnel).
    miniapp_url: str = "https://hub.kcpd.top/miniapp"

    notes_encryption_key: str = ""

    # Media storage backend for Telegram inbox files.
    # Supported values: local, r2
    media_storage_backend: str = "local"
    media_cache_dir: str = "media"

    # Cloudflare R2 (S3-compatible) settings.
    media_r2_account_id: str = ""
    media_r2_bucket: str = ""
    media_r2_access_key_id: str = ""
    media_r2_secret_access_key: str = ""
    media_r2_public_base_url: str = ""

    # E-mail channel (optional). Fill to enable reminders via email.
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_pass: str = ""
    smtp_from: str = ""
    smtp_use_tls: bool = True

    # Rate limiting
    rate_limit_enabled: bool = True
    rate_limit_default: str = "200/minute"


settings = Settings()
