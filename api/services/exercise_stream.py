"""
Exercise service handling session management and real-time data streaming.
Provides optimized session handling with continuous data updates.
"""
import asyncio
from datetime import datetime, timezone
from typing import Optional, Dict, AsyncGenerator
from dataclasses import dataclass

from api.models.exercise import ExerciseSession
from api.services.database import DatabaseService
from api.services.device import device_service
from api.utils.helpers import calculate_calories
from api.utils.logger import get_logger

logger = get_logger()


@dataclass
class SessionMetrics:
    """Real-time session metrics data structure"""
    distance_km: float  # Distance covered in kilometers
    steps: int  # Total steps taken
    duration_seconds: int  # Total session duration in seconds
    speed: float  # Current speed in km/h
    calories: Optional[int] = None  # Estimated calories burned (calculated at end)


class ExerciseStreamService:
    """
    Service for managing exercise sessions with real-time data streaming.
    Handles continuous data updates and session management.
    """

    def __init__(self):
        """Initialize the exercise streaming service"""
        self.db = DatabaseService()
        self.device = device_service
        self.current_session: Optional[ExerciseSession] = None
        self._session_active = False
        self._metrics_update_interval = 1.0  # Update interval in seconds
        self._last_metrics: Optional[SessionMetrics] = None
        self._stream_task: Optional[asyncio.Task] = None

    async def start_session(self) -> ExerciseSession:
        """
        Start a new exercise session and initialize data streaming.

        Returns:
            ExerciseSession: The newly created session object

        Raises:
            Exception: If session creation fails or device communication fails
        """
        try:
            # Create initial session record in database
            current_time = datetime.now(timezone.utc)
            query = """
                INSERT INTO exercise_sessions 
                (user_id, start_time, mode, created_at)
                VALUES (%s, %s, %s, %s)
                RETURNING id, user_id, start_time, mode
            """
            params = (1, current_time, 'manual', current_time)

            result = self.db.execute_query(query, params)
            if not result:
                raise Exception("Failed to create exercise session in database")

            # Initialize session object
            self.current_session = ExerciseSession.from_db_row(result[0])
            logger.info(f"Created new session with ID: {self.current_session.id}")

            # Start the walking pad
            await self.device.controller.start_belt()
            self._session_active = True

            # Start metrics streaming
            self._stream_task = asyncio.create_task(self._stream_session_data())
            logger.info("Session data streaming started")

            return self.current_session

        except Exception as e:
            logger.error(f"Failed to start session: {str(e)}")
            self._session_active = False
            if self._stream_task:
                self._stream_task.cancel()
            raise

    async def _stream_session_data(self):
        """
        Internal method to continuously stream session data from device.
        Runs in a separate task and updates metrics regularly.
        """
        try:
            while self._session_active:
                # Get new metrics from device
                await self.device.controller.ask_stats()
                stats = self.device.controller.last_status

                if stats:
                    # Update metrics from device data
                    self._last_metrics = SessionMetrics(
                        distance_km=stats.dist / 100,  # Convert from meters to km
                        steps=stats.steps,
                        duration_seconds=stats.time,
                        speed=stats.speed / 10  # Convert to km/h
                    )

                    # Save current metrics to database
                    await self._update_session_in_db()

                # Wait before next update
                await asyncio.sleep(self._metrics_update_interval)

        except asyncio.CancelledError:
            logger.info("Session stream cancelled")
        except Exception as e:
            logger.error(f"Error in session stream: {e}")
            self._session_active = False
            raise

    async def _update_session_in_db(self):
        """
        Update current session metrics in database.
        Called periodically during the session to maintain persistent state.
        """
        if not self._last_metrics or not self.current_session:
            return

        try:
            query = """
                UPDATE exercise_sessions 
                SET 
                    steps = %s,
                    distance_km = %s,
                    duration_seconds = %s,
                    average_speed = %s,
                    updated_at = NOW()
                WHERE id = %s
            """
            params = (
                self._last_metrics.steps,
                self._last_metrics.distance_km,
                self._last_metrics.duration_seconds,
                self._last_metrics.speed,
                self.current_session.id
            )
            self.db.execute_query(query, params)

        except Exception as e:
            logger.error(f"Failed to update session in database: {e}")

    async def get_current_metrics(self) -> Optional[SessionMetrics]:
        """
        Get the most recent session metrics.

        Returns:
            SessionMetrics if available, None otherwise
        """
        return self._last_metrics

    async def end_session(self) -> ExerciseSession:
        """
        End the current exercise session and cleanup resources.
        Calculates final metrics including calories burned.

        Returns:
            ExerciseSession: The completed session with final metrics

        Raises:
            ValueError: If no active session exists
            Exception: If session completion fails
        """
        try:
            if not self.current_session:
                raise ValueError("No active session found")

            # Stop the metrics stream
            self._session_active = False
            if self._stream_task:
                self._stream_task.cancel()
                await asyncio.wait_for(self._stream_task, timeout=5.0)

            # Stop the walking pad
            await self.device.controller.stop_belt()

            # Update session with final metrics
            end_time = datetime.now(timezone.utc)
            if self._last_metrics:
                # Get user weight for calories calculation
                user_result = self.db.execute_query(
                    "SELECT weight_kg FROM users WHERE id = %s",
                    (self.current_session.user_id,)
                )
                user_weight = user_result[0]['weight_kg'] if user_result else 70

                # Calculate calories burned
                calories = calculate_calories(
                    distance_km=self._last_metrics.distance_km,
                    duration_minutes=self._last_metrics.duration_seconds / 60,
                    weight_kg=user_weight
                )

                # Save final session data
                query = """
                    UPDATE exercise_sessions 
                    SET 
                        end_time = %s,
                        steps = %s,
                        distance_km = %s,
                        duration_seconds = %s,
                        average_speed = %s,
                        calories = %s,
                        updated_at = %s
                    WHERE id = %s
                    RETURNING *
                """

                params = (
                    end_time,
                    self._last_metrics.steps,
                    self._last_metrics.distance_km,
                    self._last_metrics.duration_seconds,
                    self._last_metrics.speed,
                    calories,
                    end_time,
                    self.current_session.id
                )

                result = self.db.execute_query(query, params)
                if result:
                    session = ExerciseSession.from_db_row(result[0])
                    self.current_session = None
                    self._last_metrics = None
                    return session

            raise Exception("Failed to update final session data")

        except Exception as e:
            logger.error(f"Error ending session: {e}", exc_info=True)
            raise


# Create singleton instance
exercise_stream_service = ExerciseStreamService()