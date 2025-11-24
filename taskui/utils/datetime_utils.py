"""DateTime utility functions for TaskUI."""

from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def format_diary_timestamp(dt: datetime, timezone_name: str = 'America/Denver') -> str:
    """
    Format datetime for diary entry display.

    Converts UTC datetime to specified timezone and formats as a compact
    timestamp suitable for diary entry display.

    Args:
        dt: UTC datetime to format (should be timezone-aware or naive UTC)
        timezone_name: IANA timezone name (e.g., 'America/Denver', 'America/New_York')

    Returns:
        Formatted string like "11/22/25 7:13AM"

    Format specification:
        - Date: MM/DD/YY (e.g., 11/22/25)
        - Time: 12-hour clock with AM/PM (e.g., 7:13AM)
        - No spaces between time and AM/PM
        - Single space between date and time

    Examples:
        >>> from datetime import datetime, timezone
        >>> dt = datetime(2025, 11, 22, 14, 13, 45, tzinfo=timezone.utc)
        >>> format_diary_timestamp(dt, 'America/Denver')
        '11/22/25 7:13AM'

        >>> dt = datetime(2025, 11, 22, 20, 30, 0, tzinfo=timezone.utc)
        >>> format_diary_timestamp(dt, 'America/New_York')
        '11/22/25 3:30PM'

    Notes:
        - If timezone_name is invalid, falls back to UTC
        - If dt is naive (no timezone), assumes UTC
        - Uses Python's zoneinfo for timezone handling (Python 3.9+)

    Raises:
        No exceptions are raised; invalid timezones fall back to UTC
    """
    # Handle naive datetime (assume UTC)
    if dt.tzinfo is None:
        from datetime import timezone as tz
        dt = dt.replace(tzinfo=tz.utc)

    # Try to convert to target timezone, fallback to UTC on error
    try:
        target_tz = ZoneInfo(timezone_name)
        local_dt = dt.astimezone(target_tz)
    except ZoneInfoNotFoundError:
        # Invalid timezone name, fallback to UTC
        from datetime import timezone as tz
        local_dt = dt.astimezone(tz.utc)

    # Format: MM/DD/YY H:MMAM/PM
    # Using %-I for hour without leading zero (Unix), %#I for Windows
    # %p gives AM/PM
    try:
        # Unix/Linux/Mac format (no leading zeros)
        formatted = local_dt.strftime('%-m/%-d/%y %-I:%M%p')
    except ValueError:
        # Windows format (no leading zeros)
        formatted = local_dt.strftime('%#m/%#d/%y %#I:%M%p')

    return formatted
