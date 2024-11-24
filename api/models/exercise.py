"""
Exercise related models and schemas
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

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
            self.steps >= 0 and
            self.steps <= 100000 and
            self.distance >= 0 and
            self.distance <= 42.2 and
            self.duration >= 0 and
            self.duration <= 24 * 3600
        )

@dataclass
class ExerciseSession:
    """Exercise session model"""
    id: Optional[int]
    user_id: int
    start_time: datetime
    end_time: Optional[datetime]
    duration_seconds: int
    distance_km: float
    steps: int
    calories: Optional[int]
    average_speed: Optional[float]
    mode: str
    created_at: datetime
    
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
