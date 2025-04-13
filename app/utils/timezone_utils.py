import pytz
from datetime import datetime
from typing import Optional

def convert_utc_to_local(timestamp_utc: datetime, timezone_str: str) -> datetime:
    """
    Convert a UTC timestamp to local time in the given timezone
    
    Args:
        timestamp_utc: Datetime in UTC
        timezone_str: Timezone string (e.g., 'America/Chicago')
        
    Returns:
        Datetime in local timezone
    """
    tz = pytz.timezone(timezone_str)
    if timestamp_utc.tzinfo is None:
        timestamp_utc = timestamp_utc.replace(tzinfo=pytz.UTC)
    return timestamp_utc.astimezone(tz)

def convert_local_to_utc(timestamp_local: datetime, timezone_str: str) -> datetime:
    """
    Convert a local timestamp to UTC
    
    Args:
        timestamp_local: Datetime in local timezone
        timezone_str: Timezone string (e.g., 'America/Chicago')
        
    Returns:
        Datetime in UTC
    """
    # Ensure the timestamp is aware of its timezone
    tz = pytz.timezone(timezone_str)
    if timestamp_local.tzinfo is None:
        timestamp_local = tz.localize(timestamp_local)
    return timestamp_local.astimezone(pytz.UTC)

def get_current_local_time(timezone_str: str) -> datetime:
    """
    Get the current time in the given timezone
    
    Args:
        timezone_str: Timezone string (e.g., 'America/Chicago')
        
    Returns:
        Current datetime in the given timezone
    """
    tz = pytz.timezone(timezone_str)
    return datetime.now(tz)

def is_valid_timezone(timezone_str: str) -> bool:
    """
    Check if a timezone string is valid
    
    Args:
        timezone_str: Timezone string to check
        
    Returns:
        True if valid, False otherwise
    """
    try:
        pytz.timezone(timezone_str)
        return True
    except pytz.exceptions.UnknownTimeZoneError:
        return False