import httpx

from app.config import settings


def send_telegram(target: str, message: str) -> tuple[bool, str]:
    if not settings.telegram_bot_token:
        return False, "Telegram bot token is not configured"

    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"

    try:
        response = httpx.post(
            url,
            json={"chat_id": target, "text": message},
            timeout=20,
        )
        if response.is_success:
            return True, response.text
        return False, f"Telegram send failed: {response.status_code} {response.text}"
    except Exception as exc:
        return False, f"Telegram send failed: {exc}"
