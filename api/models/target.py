"""
Target and goal related models
"""
from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum
from typing import Optional, Dict, Any


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
    id: int
    user_id: int
    type: str
    value: float
    start_date: date
    created_at: datetime
    end_date: Optional[date] = None
    completed: bool = False

    @classmethod
    def from_db_row(cls, row: Dict[str, Any]) -> 'Target':
        """Create a Target instance from a database row"""
        return cls(
            id=row['id'],
            user_id=row['user_id'],
            type=row['type'],
            value=float(row['value']),
            start_date=row['start_date'],
            end_date=row.get('end_date'),
            completed=row.get('completed', False),
            created_at=row['created_at']
        )

    def to_dict(self) -> dict:
        """Convert target to dictionary"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'type': self.type,
            'value': round(self.value, 2),
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'completed': self.completed,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

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
