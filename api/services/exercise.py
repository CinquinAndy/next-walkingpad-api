"""
Exercise service handling session management and statistics
"""
from datetime import datetime, timezone
from typing import Optional, List
from api.services.database import DatabaseService
from api.services.device import device_service
from api.models.exercise import (
    ExerciseSession,
    SessionData,
    ExerciseHistory,
    ExerciseStats
)
from api.utils.logger import get_logger
from api.utils.helpers import calculate_calories

logger = get_logger()


class ExerciseService:
    """Service for managing exercise sessions"""

    def __init__(self):
        """Initialize exercise service"""
        self.db = DatabaseService()
        self.device = device_service
        self.current_session: Optional[ExerciseSession] = None

    async def start_session(self) -> ExerciseSession:
        """Start a new exercise session"""
        try:
            # Start device
            await self.device.start_walking()

            # Create session record
            session = ExerciseSession(
                user_id=1,  # TODO: Get from auth
                start_time=datetime.now(timezone.utc),
                mode='manual',
                steps=0,
                distance_km=0,
                duration_seconds=0,
                calories=0
            )

            query = """
                INSERT INTO exercise_sessions 
                (user_id, start_time, mode)
                VALUES (%s, %s, %s)
                RETURNING *
            """
            result = self.db.execute_query(
                query,
                (session.user_id, session.start_time, session.mode)
            )

            self.current_session = ExerciseSession(**result[0])
            logger.info(f"Started new session: {self.current_session.id}")

            return self.current_session

        except Exception as e:
            logger.error(f"Failed to start session: {e}")
            raise

    async def end_session(self) -> ExerciseSession:
        """End current exercise session"""
        if not self.current_session:
            raise ValueError("No active session")

        try:
            # Get final stats
            stats = await self.device.get_status()

            # Calculate calories
            user_settings = await self.db.execute_query(
                "SELECT weight_kg FROM users WHERE id = %s",
                (self.current_session.user_id,)
            )
            weight_kg = user_settings[0]['weight_kg'] if user_settings else None

            calories = calculate_calories(
                stats['distance'],
                stats['time'] / 60,  # Convert to minutes
                weight_kg
            )

            # Update session record
            query = """
                UPDATE exercise_sessions 
                SET end_time = %s,
                    duration_seconds = %s,
                    distance_km = %s,
                    steps = %s,
                    calories = %s,
                    average_speed = %s
                WHERE id = %s
                RETURNING *
            """
            params = (
                datetime.now(timezone.utc),
                stats['time'],
                stats['distance'],
                stats['steps'],
                calories,
                stats['speed']
            )

            result = self.db.execute_query(
                query,
                params + (self.current_session.id,)
            )

            # Stop device
            await self.device.stop_walking()

            session = ExerciseSession(**result[0])
            self.current_session = None

            logger.info(f"Ended session {session.id}")
            return session

        except Exception as e:
            logger.error(f"Failed to end session: {e}")
            raise

    async def get_session(self, session_id: int) -> Optional[ExerciseSession]:
        """Get specific session by ID"""
        try:
            query = "SELECT * FROM exercise_sessions WHERE id = %s"
            result = self.db.execute_query(query, (session_id,))
            return ExerciseSession(**result[0]) if result else None
        except Exception as e:
            logger.error(f"Failed to get session {session_id}: {e}")
            raise

    async def get_history(
            self,
            page: int = 1,
            per_page: int = 10
    ) -> ExerciseHistory:
        """Get paginated exercise history"""
        try:
            # Get total count
            count_query = "SELECT COUNT(*) AS total FROM exercise_sessions"
            total = self.db.execute_query(count_query)[0]['total']

            # Get paginated sessions
            query = """
                SELECT * FROM exercise_sessions
                ORDER BY start_time DESC
                LIMIT %s OFFSET %s
            """
            offset = (page - 1) * per_page
            results = self.db.execute_query(query, (per_page, offset))

            sessions = [ExerciseSession(**row) for row in results]

            return ExerciseHistory(
                sessions=sessions,
                total=total,
                page=page,
                pages=(total + per_page - 1) // per_page
            )

        except Exception as e:
            logger.error(f"Failed to get exercise history: {e}")
            raise

    async def get_stats(self, period: str = 'daily') -> ExerciseStats:
        """Get exercise statistics for specified period"""
        try:
            date_trunc = {
                'daily': 'day',
                'weekly': 'week',
                'monthly': 'month'
            }.get(period, 'day')

            query = """
                SELECT 
                    COUNT(*) AS total_sessions,
                    COALESCE(SUM(distance_km), 0) AS total_distance,
                    COALESCE(SUM(steps), 0) AS total_steps,
                    COALESCE(SUM(duration_seconds), 0) AS total_duration,
                    COALESCE(SUM(calories), 0) AS total_calories,
                    COALESCE(AVG(average_speed), 0) AS average_speed
                FROM exercise_sessions
                WHERE start_time >= date_trunc(%s, CURRENT_DATE)
            """

            result = self.db.execute_query(query, (date_trunc,))[0]

            return ExerciseStats(
                total_sessions=result['total_sessions'],
                total_distance=result['total_distance'],
                total_steps=result['total_steps'],
                total_duration=result['total_duration'],
                total_calories=result['total_calories'],
                average_speed=result['average_speed'],
                period=period
            )

        except Exception as e:
            logger.error(f"Failed to get exercise stats: {e}")
            raise


# Create singleton instance
exercise_service = ExerciseService()
