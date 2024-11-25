"""
Exercise service handling session management and statistics
"""
import asyncio
from datetime import datetime, timezone
from typing import Optional, Dict

from api.models.exercise import (
    ExerciseSession,
    ExerciseHistory,
    ExerciseStats
)
from api.services.database import DatabaseService
from api.services.device import device_service
from api.utils.helpers import calculate_calories
from api.utils.logger import get_logger

logger = get_logger()


class ExerciseService:
    """Service for managing exercise sessions"""

    def __init__(self):
        """Initialize exercise service"""
        self.db = DatabaseService()
        self.device = device_service
        from api.services.security import ExerciseSecurityService  # New import
        self.security = ExerciseSecurityService(self.db, self.device)  # New security service
        self.current_session: Optional[ExerciseSession] = None
        self.db.initialize_db()
        self._last_device_metrics: Dict = {}

    async def _get_device_metrics(self) -> Dict:
        """Get current metrics from device with retries"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                status = await self.device.get_status()
                if status:
                    metrics = {
                        'distance_km': float(status.get('distance', 0)),
                        'duration_seconds': int(status.get('time', 0)),
                        'steps': int(status.get('steps', 0)),
                        'speed': float(status.get('speed', 0))
                    }
                    self._last_device_metrics = metrics
                    return metrics
            except Exception as e:
                logger.error(f"Attempt {attempt + 1}/{max_retries} failed to get device metrics: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)  # Wait before retry

        # If all retries failed, return last known metrics or zeros
        return self._last_device_metrics or {
            'distance_km': 0.0,
            'duration_seconds': 0,
            'steps': 0,
            'speed': 0.0
        }

    async def start_session(self) -> ExerciseSession:
        """
        Start a new exercise session after verifying and cleaning device state

        Returns:
            ExerciseSession: The newly created session

        Raises:
            ValueError: If device state is not clean or ready
            Exception: For other errors during session start
        """
        try:
            # Verify and clean device state before starting
            is_ready, error_message = await self.security.check_and_clean_state()
            if not is_ready:
                raise ValueError(error_message)

            logger.info("Device state verified and ready for new session")

            # Continue with existing session start code...
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

        try:
            # 1. Get current session from database if not in memory
            if not self.current_session:
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
                    raise ValueError("No active session found")

            # 2. Get device metrics before stopping
            logger.debug("Getting final device metrics")
            metrics = await self._get_device_metrics()

            # 3. Stop the walking pad
            logger.debug("Stopping walking pad")
            await self.device.stop_walking()

            # 4. Calculate session statistics
            end_time = datetime.now(timezone.utc)
            duration_seconds = max(metrics['duration_seconds'],
                                   int((end_time - self.current_session.start_time).total_seconds()))

            # Get user weight for calorie calculation
            user_result = self.db.execute_query(
                "SELECT weight_kg FROM users WHERE id = %s",
                (self.current_session.user_id,)
            )
            user_weight = user_result[0]['weight_kg'] if user_result else 70

            # Calculate calories
            duration_minutes = duration_seconds / 60
            calories = calculate_calories(
                distance_km=metrics['distance_km'],
                duration_minutes=duration_minutes,
                weight_kg=user_weight
            )

            # Calculate average speed
            average_speed = metrics['distance_km'] / (duration_minutes / 60) if duration_minutes > 0 else 0

            # 5. Update session in database
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
                end_time,
                metrics['steps'],
                metrics['distance_km'],
                duration_seconds,
                calories,
                average_speed,
                end_time,
                self.current_session.id
            )

            logger.debug(f"Updating session with metrics: {metrics}")
            result = self.db.execute_query(update_query, update_params)

            if not result:
                raise Exception("Failed to update session in database")

            # 6. Create updated session object
            updated_session = ExerciseSession.from_db_row(result[0])
            self.current_session = None

            logger.info(f"Successfully ended session {updated_session.id} with metrics: "
                        f"distance={metrics['distance_km']}km, "
                        f"steps={metrics['steps']}, "
                        f"duration={duration_seconds}s")

            return updated_session

        except Exception as e:
            logger.error(f"Error ending session: {e}", exc_info=True)
            # Ensure device is stopped even if there's an error
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
                WHERE start_time >= DATE_TRUNC(%s, CURRENT_DATE)
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
