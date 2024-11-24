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
    duration: int  # in seconds
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
    """Exercise session model"""
    id: int
    user_id: int
    start_time: datetime
    mode: str
    steps: int = 0
    distance_km: float = 0.0
    duration_seconds: int = 0
    calories: int = 0
    average_speed: float = 0.0
    end_time: Optional[datetime] = None
    max_speed: Optional[float] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @classmethod
    def from_db_row(cls, row: dict):
        """Create instance from database row"""
        if not row:
            raise ValueError("Cannot create ExerciseSession from empty data")

        logger.debug(f"Creating ExerciseSession from row: {row}")

        return cls(
            id=row['id'],
            user_id=row['user_id'],
            start_time=row['start_time'],
            end_time=row.get('end_time'),
            mode=row['mode'],
            steps=row.get('steps', 0),
            distance_km=float(row.get('distance_km', 0)),
            duration_seconds=int(row.get('duration_seconds', 0)),
            calories=int(row.get('calories', 0)),
            average_speed=float(row.get('average_speed', 0)),
            max_speed=float(row.get('max_speed')) if row.get('max_speed') is not None else None,
            created_at=row.get('created_at'),
            updated_at=row.get('updated_at')
        )

    def to_dict(self) -> dict:
        """Convert session to dictionary"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'mode': self.mode,
            'steps': self.steps,
            'distance_km': round(self.distance_km, 2),
            'duration_seconds': self.duration_seconds,
            'calories': self.calories,
            'average_speed': round(self.average_speed, 2),
            'max_speed': round(self.max_speed, 2) if self.max_speed is not None else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


@dataclass
class ExerciseHistory:
    """Exercise history pagination model"""
    sessions: list[ExerciseSession]
    total: int
    page: int
    pages: int

    def to_dict(self) -> dict:
        """Convert history to dictionary"""
        return {
            'sessions': [session.to_dict() for session in self.sessions],
            'total': self.total,
            'page': self.page,
            'pages': self.pages
        }


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
            'average_speed': round(self.average_speed, 2),
            'period': self.period
        }