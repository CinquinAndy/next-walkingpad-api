"""
Settings related models
"""
from dataclasses import dataclass, field
from typing import Optional, Dict, Any
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

    @classmethod
    def from_db_row(cls, row: Dict[str, Any]) -> 'DeviceSettings':
        """Create settings from database row, ignoring extra fields"""
        valid_fields = {
            'max_speed': float,
            'start_speed': float,
            'sensitivity': int,
            'child_lock': bool,
            'units_miles': bool,
            'created_at': datetime,
            'updated_at': datetime
        }

        # Filter and convert fields
        settings_data = {}
        for field, field_type in valid_fields.items():
            if field in row:
                # Convert field to correct type
                value = row[field]
                if field_type == bool and isinstance(value, (int, str)):
                    value = bool(value)
                elif field_type in (int, float) and value is not None:
                    value = field_type(value)
                settings_data[field] = value

        return cls(**settings_data)

    def is_valid(self) -> bool:
        """
        Validate settings values
        All speeds are in km/h
        """
        try:
            # Validate speed ranges (in km/h)
            max_speed = float(self.max_speed)
            start_speed = float(self.start_speed)
            sensitivity = int(self.sensitivity)

            # Check individual constraints
            max_speed_valid = 1.0 <= max_speed <= 6.0
            start_speed_valid = 1.0 <= start_speed <= 3.0
            sensitivity_valid = 1 <= sensitivity <= 3

            # Check speed relationship
            speed_relation_valid = start_speed <= max_speed

            if not all([max_speed_valid, start_speed_valid,
                        sensitivity_valid, speed_relation_valid]):
                logger.warning(
                    f"Invalid settings validation results:\n"
                    f"- max_speed_valid ({max_speed}): {max_speed_valid}\n"
                    f"- start_speed_valid ({start_speed}): {start_speed_valid}\n"
                    f"- sensitivity_valid ({sensitivity}): {sensitivity_valid}\n"
                    f"- speed_relation_valid: {speed_relation_valid}"
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
            'child_lock': bool(self.child_lock),
            'units_miles': bool(self.units_miles),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
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
