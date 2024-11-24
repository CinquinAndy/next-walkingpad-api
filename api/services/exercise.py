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
        self.db.initialize_db()

    async def start_session(self) -> ExerciseSession:
        """Start a new exercise session"""
        try:
            # Start device
            await self.device.start_walking()

            current_time = datetime.now(timezone.utc)

            # Insert into database
            query = """
                INSERT INTO exercise_sessions 
                (
                    user_id, 
                    start_time, 
                    mode, 
                    steps, 
                    distance_km, 
                    duration_seconds, 
                    calories, 
                    average_speed,
                    created_at
                )
                VALUES 
                (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
                RETURNING 
                    id, 
                    user_id, 
                    start_time, 
                    mode, 
                    steps, 
                    distance_km, 
                    duration_seconds, 
                    calories, 
                    average_speed,
                    created_at
            """

            params = (
                1,  # user_id
                current_time,  # start_time
                'manual',  # mode
                0,  # steps
                0.0,  # distance_km
                0,  # duration_seconds
                0,  # calories
                0.0,  # average_speed
                current_time  # created_at
            )

            logger.debug(f"Executing insert with params: {params}")
            result = self.db.execute_query(query, params)

            if not result:
                logger.error("Insert query did not return any results")
                raise Exception("Failed to create exercise session - no data returned")

            logger.debug(f"Insert result: {result}")

            # Create session from database result
            self.current_session = ExerciseSession.from_db_row(result[0])
            logger.info(f"Started new session: {self.current_session.id}")

            return self.current_session

        except Exception as e:
            logger.error(f"Failed to start session: {str(e)}")
            # Ensure device is stopped in case of error
            try:
                await self.device.stop_walking()
            except:
                pass
            raise

    async def end_session(self) -> ExerciseSession:
        """End current exercise session"""
        logger.info("Attempting to end exercise session")

        if not self.current_session:
            # Try to find the last active session
            query = """
                SELECT * FROM exercise_sessions 
                WHERE end_time IS NULL 
                ORDER BY start_time DESC 
                LIMIT 1
            """
            result = self.db.execute_query(query)

            if result:
                logger.info("Found active session in database")
                self.current_session = ExerciseSession.from_db_row(result[0])
            else:
                logger.error("No active session found in memory or database")
                raise ValueError("No active exercise session found. Please start a session first.")
        """End current exercise session"""
        logger.info("Attempting to end exercise session")

        if not self.current_session:
            logger.error("No active session found")
            raise ValueError("No active session")

        try:
            logger.debug("Stopping walking pad device")
            await self.device.stop_walking()

            logger.debug("Getting device status")
            status = await self.device.get_status()
            logger.debug(f"Device status received: {status}")

            # Get device metrics with fallbacks to 0
            time_elapsed = getattr(status, 'time', 0)
            distance = getattr(status, 'dist', 0)
            steps = getattr(status, 'steps', 0)

            # Calculate duration and average speed
            duration_minutes = time_elapsed / 60 if time_elapsed else 0
            average_speed = 0.0
            if time_elapsed > 0:
                average_speed = (distance / (time_elapsed / 3600))

            # Get user weight
            user_weight = 70  # default weight
            user_result = self.db.execute_query(
                "SELECT weight_kg FROM users WHERE id = %s",
                (self.current_session.user_id,)
            )
            if user_result:
                user_weight = user_result[0]['weight_kg']

            # Calculate calories
            calories = calculate_calories(
                distance_km=distance,
                duration_minutes=duration_minutes,
                weight_kg=user_weight
            )

            current_time = datetime.now(timezone.utc)

            update_query = """
                       UPDATE exercise_sessions 
                       SET 
                           end_time = %s,
                           steps = %s,
                           distance_km = %s,
                           duration_seconds = %s,
                           calories = %s,
                           average_speed = %s,
                           updated_at = %s
                       WHERE id = %s
                       RETURNING *
                   """

            update_params = (
                current_time,
                steps,
                distance,
                time_elapsed,
                calories,
                average_speed,
                current_time,
                self.current_session.id
            )

            logger.debug(f"Executing update query with params: {update_params}")
            result = self.db.execute_query(update_query, update_params)

            if not result:
                logger.error("Update query returned no results")
                raise Exception("Failed to update exercise session")

            logger.debug(f"Update query result: {result}")
            updated_session = ExerciseSession.from_db_row(result[0])

            self.current_session = None
            logger.info(f"Successfully ended session {updated_session.id}")

            return updated_session

        except Exception as e:
            logger.error(f"Error ending session: {str(e)}", exc_info=True)
            try:
                await self.device.stop_walking()
            except Exception as stop_error:
                logger.error(f"Failed to stop device during error handling: {stop_error}")
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
