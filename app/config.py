from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Personal Automation Hub"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    app_api_key: str = "change-me"

    database_url: str = "sqlite:///./automation_hub.db"
    scheduler_poll_seconds: int = 30
    daily_summary_enabled: bool = False
    daily_summary_time_utc: str = "19:00"
    daily_summary_channel: str = "telegram"
    daily_summary_target: str = ""

    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    telegram_bot_polling_enabled: bool = True
    telegram_bot_poll_timeout_seconds: int = 20
    notes_encryption_key: str = ""


settings = Settings()
