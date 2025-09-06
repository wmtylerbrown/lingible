"""Timezone utilities for consistent time handling across the application."""

from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo


def get_central_timezone() -> ZoneInfo:
    """Get Central Time timezone (handles both CST and CDT automatically)."""
    return ZoneInfo("America/Chicago")


def get_central_midnight_tomorrow() -> datetime:
    """Get tomorrow's midnight in Central Time, converted to UTC for storage."""
    central_tz = get_central_timezone()
    
    # Get current time in Central Time
    now_central = datetime.now(central_tz)
    
    # Get tomorrow's midnight in Central Time
    tomorrow_midnight_central = now_central.replace(
        hour=0, minute=0, second=0, microsecond=0
    ) + timedelta(days=1)
    
    # Convert to UTC for storage
    tomorrow_midnight_utc = tomorrow_midnight_central.astimezone(timezone.utc)
    
    return tomorrow_midnight_utc


def get_central_midnight_today() -> datetime:
    """Get today's midnight in Central Time, converted to UTC for storage."""
    central_tz = get_central_timezone()
    
    # Get current time in Central Time
    now_central = datetime.now(central_tz)
    
    # Get today's midnight in Central Time
    today_midnight_central = now_central.replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    
    # Convert to UTC for storage
    today_midnight_utc = today_midnight_central.astimezone(timezone.utc)
    
    return today_midnight_utc


def is_new_day_central_time(reset_daily_at: datetime) -> bool:
    """Check if it's a new day in Central Time based on the reset date."""
    central_tz = get_central_timezone()
    
    # Get current time in Central Time
    now_central = datetime.now(central_tz)
    
    # Get today's midnight in Central Time
    today_midnight_central = now_central.replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    
    # Convert reset date to Central Time for comparison
    reset_central = reset_daily_at.astimezone(central_tz)
    
    # It's a new day if the reset date is before today's midnight in Central Time
    return reset_central < today_midnight_central
