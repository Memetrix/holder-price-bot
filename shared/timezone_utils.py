"""
Timezone utilities for HOLDER Price Bot
Stores all timestamps in UTC, displays in UTC+3 (Moscow time)
"""

from datetime import datetime, timezone, timedelta
from typing import Optional

# Moscow timezone (UTC+3)
MOSCOW_TZ = timezone(timedelta(hours=3))


def utc_now() -> datetime:
    """
    Get current UTC time as timezone-aware datetime.
    Use this instead of datetime.now() for all timestamps.
    """
    return datetime.now(timezone.utc)


def utc_now_iso() -> str:
    """
    Get current UTC time as ISO format string.
    Use this for database storage.
    """
    return utc_now().isoformat()


def to_moscow_time(dt: datetime) -> datetime:
    """
    Convert UTC datetime to Moscow time (UTC+3).

    Args:
        dt: UTC datetime (timezone-aware or naive, assumed UTC if naive)

    Returns:
        Datetime in Moscow timezone
    """
    if dt.tzinfo is None:
        # Assume naive datetime is UTC
        dt = dt.replace(tzinfo=timezone.utc)

    return dt.astimezone(MOSCOW_TZ)


def format_moscow_time(dt: datetime, fmt: str = '%Y-%m-%d %H:%M:%S') -> str:
    """
    Format UTC datetime as Moscow time string.

    Args:
        dt: UTC datetime (timezone-aware or naive, assumed UTC if naive)
        fmt: strftime format string

    Returns:
        Formatted string in Moscow time
    """
    moscow_dt = to_moscow_time(dt)
    return moscow_dt.strftime(fmt)


def parse_iso_to_moscow(iso_string: str, fmt: str = '%Y-%m-%d %H:%M:%S') -> str:
    """
    Parse ISO timestamp string (assumed UTC) and format as Moscow time.

    Args:
        iso_string: ISO format timestamp string
        fmt: strftime format string

    Returns:
        Formatted string in Moscow time
    """
    try:
        # Parse ISO string
        dt = datetime.fromisoformat(iso_string.replace('Z', '+00:00'))
        return format_moscow_time(dt, fmt)
    except (ValueError, AttributeError):
        return iso_string  # Return original if parsing fails


def moscow_now() -> datetime:
    """
    Get current time in Moscow timezone.
    Note: This is for display only. Always store UTC in database!
    """
    return utc_now().astimezone(MOSCOW_TZ)


def moscow_now_str(fmt: str = '%Y-%m-%d %H:%M:%S') -> str:
    """
    Get current Moscow time as formatted string.
    Note: This is for display only. Always store UTC in database!
    """
    return moscow_now().strftime(fmt)
