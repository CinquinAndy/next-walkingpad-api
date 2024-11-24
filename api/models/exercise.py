"""
Exercise service handling exercise session logic
"""
from datetime import datetime, timezone
from typing import Optional
from api.services.database import DatabaseService
from api.services.device import device_service
from api.models.exercise import (
    ExerciseSession,
    SessionData,
    ExerciseHistory,
    ExerciseStats
)


class ExerciseService:
    """Service for managing exercise sessions"""

    def __init__(self):
        """Initialize the exercise service"""
        self.db = DatabaseService()
        self.current_session_id: Optional[int] = None

    async def start_session(self) -> ExerciseSession:
        """Start a new exercise session"""
        # Start the device
        await device_service.start_walking()

        # Create session record
        query = """
            INSERT INTO exercise_sessions 
            (user_id, start_time, mode)
            VALUES ((SELECT id FROM users LIMIT 1), %s, %s)
            RETURNING id
        """
        result = self.db.execute_query(
            query,
            (datetime.now(timezone.utc), 'manual')
        )

        self.current_session_id = result[0]['id']
        return await self.get_session(self.current_session_id)

    async def end_session(self) -> ExerciseSession:
        """End the current exercise session"""
        if not self.current_session_id:
            raise ValueError("No active session")

        # Get final stats from device
        stats = await device_service.get_stats()

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
            stats.get('calories', 0),
            stats['speed']
        )

        result = self.db.execute_query(query, params + (self.current_session_id,))

        # Stop the device
        await device_service.stop_walking()

        self.current_session_id = None
        return ExerciseSession(**result[0])

    async def get_session(self, session_id: int) -> Optional[ExerciseSession]:
        """Get a specific session by ID"""
        query = "SELECT * FROM exercise_sessions WHERE id = %s"
        result = self.db.execute_query(query, (session_id,))
        return ExerciseSession(**result[0]) if result else None

    async def get_current_session(self) -> Optional[ExerciseSession]:
        """Get the current active session"""
        if not self.current_session_id:
            return None
        return await self.get_session(self.current_session_id)

    async def save_session(self, data: SessionData) -> ExerciseSession:
        """Save a new exercise session"""
        query = """
            INSERT INTO exercise_sessions 
            (user_id, start_time, end_time, duration_seconds, 
             distance_km, steps, calories, average_speed, mode)
            VALUES ((SELECT id FROM users LIMIT 1), %s, %s, %s, %s, %s, %s, %s, 'manual')
            RETURNING *
        """
        now = datetime.now(timezone.utc)
        params = (
            now - timedelta(seconds=data.duration),
            now,
            data.duration,
            data.distance,
            data.steps,
            data.calories,
            data.avg_speed
        )

        result = self.db.execute_query(query, params)
        return ExerciseSession(**result[0])

    async def get_history(
            self,
            page: int = 1,
            per_page: int = 10
    ) -> ExerciseHistory:
        """Get paginated exercise history"""
        query = """
            SELECT COUNT(*) as total FROM exercise_sessions
            WHERE user_id = (SELECT id FROM users LIMIT 1)
        """
        total = self.db.execute_query(query)[0]['total']

        query = """
            SELECT * FROM exercise_sessions
            WHERE user_id = (SELECT id FROM users LIMIT 1)
            ORDER BY start_time DESC
            LIMIT %s OFFSET %s
        """
        offset = (page - 1) * per_page
        results = self.db.execute_query(query, (per_page, offset))

        return ExerciseHistory(
            sessions=[ExerciseSession(**row) for row in results],
            total=total,
            page=page,
            pages=(total + per_page - 1) // per_page
        )

    async def get_stats(self, period: str = 'daily') -> ExerciseStats:
        """Get exercise statistics for the specified period"""
        date_trunc = {
            'daily': 'day',
            'weekly': 'week',
            'monthly': 'month'
        }.get(period, 'day')

        query = """
            SELECT 
                COUNT(*) as total_sessions,
                SUM(distance_km) as total_distance,
                SUM(steps) as total_steps,
                SUM(duration_seconds) as total_duration,
                SUM(calories) as total_calories,
                AVG(average_speed) as average_speed
            FROM exercise_sessions
            WHERE user_id = (SELECT id FROM users LIMIT 1)
            AND start_time >= date_trunc(%s, CURRENT_DATE)
        """

        result = self.db.execute_query(query, (date_trunc,))[0]
        return ExerciseStats(
            total_sessions=result['total_sessions'],
            total_distance=result['total_distance'] or 0,
            total_steps=result['total_steps'] or 0,
            total_duration=result['total_duration'] or 0,
            total_calories=result['total_calories'] or 0,
            average_speed=result['average_speed'] or 0,
            period=period
        )


# Create a singleton instance
exercise_service = ExerciseService()
