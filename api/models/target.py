"""
Target and goal related models
"""
from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional
from enum import Enum

class TargetType(str, Enum):
    """Target types enum"""
    DISTANCE = 'distance'    # Distance in kilometers
    STEPS = 'steps'         # Number of steps
    CALORIES = 'calories'   # Calories burned
    DURATION = 'duration'   # Duration in minutes

    @classmethod
    def values(cls) -> list[str]:
        """Get all valid target types"""
        return [member.value for member in cls]

@dataclass
class Target:
    """Exercise target model"""
    id: Optional[int] = None
    type: str = TargetType.STEPS.value
    value: float = 0.0
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    completed: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def is_valid(self) -> bool:
        """Validate target"""
        if self.type not in TargetType.values():
            return False

        # Validate value ranges based on type
        if self.type == TargetType.DISTANCE:
            return 0 < self.value <= 42.2  # Marathon distance
        elif self.type == TargetType.STEPS:
            return 0 < self.value <= 100000  # Daily steps
        elif self.type == TargetType.CALORIES:
            return 0 < self.value <= 5000  # Daily calories
        elif self.type == TargetType.DURATION:
            return 0 < self.value <= 24 * 60  # 24 hours in minutes

        return False

    def to_dict(self) -> dict:
        """Convert target to dictionary"""
        return {
            'id': self.id,
            'type': self.type,
            'value': self.value,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'completed': self.completed
        }

@dataclass
class TargetProgress:
    """Target progress tracking"""
    target: Target
    current_value: float
    progress: float  # Percentage (0-100)
    completed: bool
    last_updated: Optional[datetime] = None

    def to_dict(self) -> dict:
        """Convert progress to dictionary"""
        return {
            'target': self.target.to_dict(),
            'current_value': round(self.current_value, 2),
            'progress': round(self.progress, 1),
            'completed': self.completed,
            'last_updated': self.last_updated.isoformat() if self.last_updated else None
        }
