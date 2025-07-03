from datetime import datetime
from typing import List
from zoneinfo import ZoneInfo, available_timezones

from tzlocal import get_localzone_name


def get_local_timezone() -> str:
    """Return the system's current local timezone name."""
    try:
        return get_localzone_name()
    except ImportError:
        # Fallback: return UTC if tzlocal is not available
        return "UTC"


def get_current_time_in_timezone(timezone_name: str) -> str:
    """
    Given a timezone name (e.g., 'Asia/Kolkata'),
    return the current time as a string.
    """
    if timezone_name not in available_timezones():
        raise ValueError(f"Invalid timezone name: {timezone_name}")

    tz = ZoneInfo(timezone_name)
    now = datetime.now(tz)
    return now.strftime("%Y-%m-%d %H:%M:%S %Z")


def list_available_timezones(limit: int = 10) -> List[str]:
    """Return a sample of available timezones."""
    return sorted(available_timezones())[:limit]


def main() -> None:
    local_tz = get_local_timezone()
    print(f"Your local timezone: {local_tz}")
    print(f"Sample timezones: {list_available_timezones()}\n")

    user_input = input("Enter a timezone (e.g., 'Europe/London'): ").strip()
    try:
        current_time = get_current_time_in_timezone(user_input)
        print(f"Current time in {user_input}: {current_time}")
    except ValueError as e:
        print(f"{e}")


if __name__ == "__main__":
    main()

# Your local timezone: Asia/Kolkata
# Sample timezones: ['Africa/Abidjan', 'Africa/Accra', ...]

# Enter a timezone (e.g., 'Europe/London'): America/New_York
# Current time in America/New_York: 2025-07-02 08:52:23 EDT
