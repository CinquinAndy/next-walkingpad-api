"""
Settings related models
"""
from dataclasses import dataclass
from typing import Optional
from datetime import datetime

@dataclass
class DeviceSettings:
    """Device settings model"""
    max_speed: int = 60          # Maximum speed (10-60)
    start_speed: int = 20        # Starting speed (10-30)
    sensitivity: int = 2         # Sensitivity (1=high, 2=medium, 3=low)
    child_lock: bool = False     # Child lock enabled
    units_miles: bool = False    # Use miles instead of kilometers
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def is_valid(self) -> bool:
        """Validate settings values"""
        return (
            10 <= self.max_speed <= 60 and
            10 <= self.start_speed <= 30 and
            1 <= self.sensitivity <= 3 and
            self.start_speed <= self.max_speed
        )

    def to_dict(self) -> dict:
        """Convert settings to dictionary"""
        return {
            'max_speed': self.max_speed / 10,  # Convert to km/h
            'start_speed': self.start_speed / 10,
            'sensitivity': self.sensitivity,
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
