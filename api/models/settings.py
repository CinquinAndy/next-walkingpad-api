"""
Settings related models
"""
from dataclasses import dataclass
from typing import Optional
from datetime import datetime
from api.utils.logger import get_logger

logger = get_logger()

@dataclass
class DeviceSettings:
    """Device settings model"""
    max_speed: float = 6.0          # Maximum speed in km/h (1.0-6.0)
    start_speed: float = 2.0        # Starting speed in km/h (1.0-3.0)
    sensitivity: int = 2            # Sensitivity (1=high, 2=medium, 3=low)
    child_lock: bool = False        # Child lock enabled
    units_miles: bool = False       # Use miles instead of kilometers
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def is_valid(self) -> bool:
        """
        Validate settings values
        All speeds are in km/h
        """
        try:
            # Validate speed ranges (in km/h)
            max_speed_valid = 1.0 <= float(self.max_speed) <= 6.0
            start_speed_valid = 1.0 <= float(self.start_speed) <= 3.0
            speed_relation_valid = float(self.start_speed) <= float(self.max_speed)
            sensitivity_valid = 1 <= int(self.sensitivity) <= 3

            if not all([max_speed_valid, start_speed_valid,
                        sensitivity_valid, speed_relation_valid]):
                logger.warning(
                    f"Invalid settings - max_speed: {self.max_speed} km/h, "
                    f"start_speed: {self.start_speed} km/h, "
                    f"sensitivity: {self.sensitivity}, "
                    f"speed_relation_valid: {speed_relation_valid}"
                )
                return False

            return True

        except (ValueError, TypeError) as e:
            logger.error(f"Validation error: {e}")
            return False

    def to_device_units(self) -> dict:
        """Convert settings to device units"""
        return {
            'max_speed': int(float(self.max_speed) * 10),  # km/h to device units
            'start_speed': int(float(self.start_speed) * 10),
            'sensitivity': int(self.sensitivity),
            'child_lock': self.child_lock,
            'units_miles': self.units_miles
        }

    def to_dict(self) -> dict:
        """Convert settings to dictionary (in km/h)"""
        return {
            'max_speed': float(self.max_speed),
            'start_speed': float(self.start_speed),
            'sensitivity': int(self.sensitivity),
            'child_lock': self.child_lock,
            'units_miles': self.units_miles
        }

@dataclass
class UserSettings:
    """User settings and profile model"""
    id: int
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    height_cm: Optional[int] = None
    weight_kg: Optional[float] = None
    profile_picture_url: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @property
    def bmi(self) -> Optional[float]:
        """Calculate BMI if height and weight are available"""
        if self.height_cm and self.weight_kg:
            height_m = self.height_cm / 100
            return round(self.weight_kg / (height_m * height_m), 1)
        return None

    def to_dict(self) -> dict:
        """Convert user settings to dictionary"""
        return {
            'id': self.id,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'email': self.email,
            'height': self.height_cm,
            'weight': self.weight_kg,
            'bmi': self.bmi,
            'profile_picture_url': self.profile_picture_url
        }
