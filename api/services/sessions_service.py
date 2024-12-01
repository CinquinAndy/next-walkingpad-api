"""
Sessions management service for tracking workout activities
Handles session lifecycle, statistics, and daily tracking
"""
from datetime import datetime, timezone, date
from typing import Optional, Dict, List
from dataclasses import dataclass

from api.services.database import DatabaseService
from api.utils.logger import get_logger

logger = get_logger()


@dataclass
class DailyStats:
    """Daily workout statistics"""
    date: date
    total_distance: float
    total_steps: int
    total_duration: int
    total_calories: int
    sessions_count: int
    average_speed: float


@dataclass
class Session:
    """Workout session data"""
    id: int
    start_time: datetime
    end_time: Optional[datetime]
    distance_km: float
    steps: int
    duration_seconds: int
    calories: int
    average_speed: float


class SessionsService:
    """Service for managing workout sessions and statistics"""

    def __init__(self, db: DatabaseService):
        self.db = db
        self.active_session_id: Optional[int] = None

    async def start_session(self) -> Session:
        """Start a new workout session"""
        try:
            if self.active_session_id:
                raise ValueError("A session is already active")

            query = """
                INSERT INTO exercise_sessions 
                (start_time, user_id, mode)
                VALUES (NOW(), 1, 'manual')
                RETURNING id, start_time
            """
            result = self.db.execute_query(query)

            if not result:
                raise Exception("Failed to create session")

            self.active_session_id = result[0]['id']
            logger.info(f"Started new session: {self.active_session_id}")

            return Session(
                id=result[0]['id'],
                start_time=result[0]['start_time'],
                end_time=None,
                distance_km=0,
                steps=0,
                duration_seconds=0,
                calories=0,
                average_speed=0
            )

        except Exception as e:
            logger.error(f"Failed to start session: {e}")
            raise

    async def update_session_metrics(self, metrics: Dict) -> None:
        """Update current session with latest metrics"""
        if not self.active_session_id:
            return

        try:
            query = """
                UPDATE exercise_sessions 
                SET 
                    distance_km = %s,
                    steps = %s,
                    duration_seconds = %s,
                    calories = %s,
                    average_speed = %s,
                    updated_at = NOW()
                WHERE id = %s
            """
            params = (
                metrics['distance_km'],
                metrics['steps'],
                metrics['time'],
                self._calculate_calories(metrics),
                metrics['speed'],
                self.active_session_id
            )
            self.db.execute_query(query, params)

        except Exception as e:
            logger.error(f"Failed to update session metrics: {e}")

    async def end_session(self) -> Session:
        """End current workout session"""
        if not self.active_session_id:
            raise ValueError("No active session")

        try:
            query = """
                UPDATE exercise_sessions 
                SET 
                    end_time = NOW(),
                    updated_at = NOW()
                WHERE id = %s
                RETURNING *
            """
            result = self.db.execute_query(query, (self.active_session_id,))

            if not result:
                raise Exception("Failed to end session")

            session_data = result[0]
            self.active_session_id = None

            return Session(
                id=session_data['id'],
                start_time=session_data['start_time'],
                end_time=session_data['end_time'],
                distance_km=session_data['distance_km'],
                steps=session_data['steps'],
                duration_seconds=session_data['duration_seconds'],
                calories=session_data['calories'],
                average_speed=session_data['average_speed']
            )

        except Exception as e:
            logger.error(f"Failed to end session: {e}")
            raise

    async def get_daily_stats(self, target_date: date = None) -> DailyStats:
        """Get statistics for a specific day"""
        target_date = target_date or date.today()

        try:
            query = """
                SELECT 
                    COUNT(*) as sessions_count,
                    COALESCE(SUM(distance_km), 0) as total_distance,
                    COALESCE(SUM(steps), 0) as total_steps,
                    COALESCE(SUM(duration_seconds), 0) as total_duration,
                    COALESCE(SUM(calories), 0) as total_calories,
                    COALESCE(AVG(average_speed), 0) as average_speed
                FROM exercise_sessions
                WHERE DATE(start_time) = %s
                AND end_time IS NOT NULL
            """
            result = self.db.execute_query(query, (target_date,))[0]

            return DailyStats(
                date=target_date,
                total_distance=round(result['total_distance'], 2),
                total_steps=result['total_steps'],
                total_duration=result['total_duration'],
                total_calories=result['total_calories'],
                sessions_count=result['sessions_count'],
                average_speed=round(result['average_speed'], 2)
            )

        except Exception as e:
            logger.error(f"Failed to get daily stats: {e}")
            raise

    def _calculate_calories(self, metrics: Dict) -> int:
        """Calculate calories based on metrics"""
        # Simplified calorie calculation - can be enhanced
        MET = 3.5  # Metabolic equivalent for walking
        WEIGHT = 70  # Default weight in kg - can be fetched from user profile

        hours = metrics['time'] / 3600
        return int(MET * WEIGHT * hours * 1.036)  # 1.036 factor for kcal conversion


# Create singleton instance
sessions_service = SessionsService(DatabaseService())