from __future__ import annotations

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from app.config import settings


def get_app_timezone() -> ZoneInfo:
    try:
        return ZoneInfo(settings.app_timezone)
    except Exception:
        return ZoneInfo("UTC")


def utc_now_naive() -> datetime:
    """Return current UTC time as a naive datetime for DB columns without tzinfo."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def normalize_client_datetime(value: datetime | None) -> datetime | None:
    """Normalize inbound datetime to UTC-naive for persistence.

    If the client sent a timezone-aware datetime, convert it to UTC and drop tzinfo.
    If the client sent a naive datetime, interpret it in app timezone first.
    """
    if value is None:
        return None

    if value.tzinfo is None:
        local_value = value.replace(tzinfo=get_app_timezone())
    else:
        local_value = value

    return local_value.astimezone(timezone.utc).replace(tzinfo=None)


def local_today_string() -> str:
    """Current date in app timezone, formatted as YYYY-MM-DD."""
    return datetime.now(get_app_timezone()).strftime("%Y-%m-%d")


def local_day_bounds_utc_naive() -> tuple[datetime, datetime]:
    """UTC-naive bounds for today's local day in app timezone.

    Useful for querying UTC-naive DB timestamps while presenting local-day metrics.
    """
    tz = get_app_timezone()
    now_local = datetime.now(tz)
    day_start_local = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
    day_end_local = day_start_local + timedelta(days=1)
    start_utc_naive = day_start_local.astimezone(timezone.utc).replace(tzinfo=None)
    end_utc_naive = day_end_local.astimezone(timezone.utc).replace(tzinfo=None)
    return start_utc_naive, end_utc_naive
