"""
Utility functions for the application
"""
from datetime import datetime, date
from typing import Optional


def calculate_calories(distance_km: float, duration_minutes: float, weight_kg: float) -> float:
    """Calculate calories burned during exercise"""
    if duration_minutes <= 0 or distance_km <= 0:
        return 0.0

    try:
        speed_kph = distance_km / (duration_minutes / 60)
        # MET value for walking based on speed
        if speed_kph < 4:
            met = 2.0
        elif speed_kph < 6:
            met = 3.5
        else:
            met = 5.0

        # Calories = MET × weight (kg) × duration (hours)
        calories = met * weight_kg * (duration_minutes / 60)
        return round(calories, 2)
    except ZeroDivisionError:
        return 0.0


def format_duration(seconds: int) -> str:
    """Format duration in seconds to HH:MM:SS"""
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    remaining_seconds = seconds % 60

    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{remaining_seconds:02d}"
    return f"{minutes:02d}:{remaining_seconds:02d}"


def parse_date(date_str: str) -> Optional[date]:
    """Parse date string in various formats"""
    formats = [
        "%Y-%m-%d",
        "%d-%m-%Y",
        "%Y/%m/%d",
        "%d/%m/%Y"
    ]

    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue

    return None


def calculate_streak(dates: list[date]) -> int:
    """Calculate consecutive days streak"""
    if not dates:
        return 0

    dates = sorted(set(dates), reverse=True)
    streak = 1

    for i in range(1, len(dates)):
        days_diff = (dates[i - 1] - dates[i]).days
        if days_diff == 1:
            streak += 1
        else:
            break

    return streak


def is_valid_bluetooth_address(address: str) -> bool:
    """Validate Bluetooth MAC address format"""
    if not address:
        return False

    parts = address.split(':')
    if len(parts) != 6:
        return False

    try:
        return all(0 <= int(part, 16) <= 255 for part in parts)
    except ValueError:
        return False


def create_error_response(message: str, details: Optional[str] = None) -> dict:
    """Create standardized error response"""
    response = {'error': message}
    if details:
        response['details'] = details
    return response


