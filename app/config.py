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

    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    telegram_bot_polling_enabled: bool = True
    telegram_bot_poll_timeout_seconds: int = 20
    # If set, the bot registers a webhook instead of using long-polling.
    # Must be a publicly reachable HTTPS URL, e.g. https://yourdomain.com/telegram/webhook
    telegram_webhook_url: str = ""
    # Random secret token used to validate incoming webhook requests from Telegram.
    # Generate with: python -c "import secrets; print(secrets.token_hex(32))"
    telegram_webhook_secret: str = ""

    notes_encryption_key: str = ""

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
