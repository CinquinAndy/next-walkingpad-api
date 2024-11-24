"""
Exercise related models and schemas
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from api.utils.logger import logger


@dataclass
class SessionData:
    """Exercise session data model"""
    steps: int
    distance: float  # in kilometers
    duration: int    # in seconds
    calories: Optional[int] = None
    avg_speed: Optional[float] = None
    
    def is_valid(self) -> bool:
        """Validate session data"""
        return (
                0 <= self.steps <= 100000 and
                0 <= self.distance <= 42.2 and
                0 <= self.duration <= 24 * 3600
        )

@dataclass
class ExerciseSession:
    def __init__(
        self,
        id: int,
        user_id: int,
        start_time: datetime,
        mode: str,
        steps: int = 0,
        distance_km: float = 0.0,
        duration_seconds: int = 0,
        calories: int = 0,
        average_speed: float = 0.0,
        end_time: datetime = None,
        created_at: datetime = None,
        updated_at: datetime = None
    ):
        self.id = id
        self.user_id = user_id
        self.start_time = start_time
        self.end_time = end_time
        self.mode = mode
        self.steps = steps
        self.distance_km = distance_km
        self.duration_seconds = duration_seconds
        self.calories = calories
        self.average_speed = average_speed
        self.created_at = created_at
        self.updated_at = updated_at

    @classmethod
    def from_db_row(cls, row: dict):
        """Create instance from database row"""
        if not row:
            raise ValueError("Cannot create ExerciseSession from empty data")

        # Log the row data for debugging
        logger.debug(f"Creating ExerciseSession from row: {row}")

        # Ensure all required fields are present
        required_fields = ['user_id', 'start_time', 'mode']
        for field in required_fields:
            if field not in row:
                raise ValueError(f"Missing required field: {field}")

        return cls(
            id=row.get('id'),
            user_id=row['user_id'],
            start_time=row['start_time'],
            end_time=row.get('end_time'),
            mode=row['mode'],
            steps=row.get('steps', 0),
            distance_km=float(row.get('distance_km', 0)),
            duration_seconds=int(row.get('duration_seconds', 0)),
            calories=int(row.get('calories', 0)),
            average_speed=float(row.get('average_speed', 0)),
            created_at=row.get('created_at')
        )

    def to_dict(self) -> dict:
        """Convert session to dictionary"""
        return {
            'id': self.id,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'duration': self.duration_seconds,
            'distance': self.distance_km,
            'steps': self.steps,
            'calories': self.calories,
            'average_speed': self.average_speed,
            'mode': self.mode
        }

@dataclass
class ExerciseHistory:
    """Exercise history pagination model"""
    sessions: list[ExerciseSession]
    total: int
    page: int
    pages: int

@dataclass
class ExerciseStats:
    """Exercise statistics model"""
    total_sessions: int
    total_distance: float
    total_steps: int
    total_duration: int
    total_calories: int
    average_speed: float
    period: str  # daily, weekly, monthly
    
    def to_dict(self) -> dict:
        """Convert stats to dictionary"""
        return {
            'total_sessions': self.total_sessions,
            'total_distance': round(self.total_distance, 2),
            'total_steps': self.total_steps,
            'total_duration': self.total_duration,
            'total_calories': self.total_calories,
            'average_speed': round(self.average_speed, 1),
            'period': self.period
        }
