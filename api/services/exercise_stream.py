"""
Enhanced exercise streaming service with better error handling and device reconnection
"""
from datetime import datetime, timezone
from dataclasses import dataclass
from typing import Optional
import asyncio

from api.models.exercise import ExerciseSession
from api.services.database import DatabaseService
from api.services.device import device_service
from api.utils.helpers import calculate_calories
from api.utils.logger import get_logger

logger = get_logger()

@dataclass
class StreamMetrics:
    """Real-time session metrics"""
    distance_km: float = 0.0
    steps: int = 0
    duration_seconds: int = 0
    speed: float = 0.0
    calories: Optional[int] = None
    belt_state: Optional[str] = None

class ExerciseStreamService:
    """Service for managing exercise sessions with optimized streaming"""
    MAX_RECONNECT_ATTEMPTS = 3
    RECONNECT_DELAY = 2.0  # seconds

    def __init__(self):
        """Initialize streaming service"""
        self.db = DatabaseService()
        self.device = device_service
        self.current_session: Optional[ExerciseSession] = None
        self._session_active = False
        self._metrics_update_interval = 1.0
        self._last_metrics: Optional[StreamMetrics] = None
        self._stream_task: Optional[asyncio.Task] = None

    async def start_session(self) -> ExerciseSession:
        """Start new exercise session with retry logic for device connection"""
        logger.info("Starting new exercise session")

        try:
            # Create session in database first
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
                raise Exception("Failed to create exercise session")

            self.current_session = ExerciseSession.from_db_row(result[0])
            logger.info(f"Created session: {self.current_session.id}")

            # Attempt device connection with retries
            for attempt in range(self.MAX_RECONNECT_ATTEMPTS):
                try:
                    logger.info(f"Connecting to device (attempt {attempt + 1}/{self.MAX_RECONNECT_ATTEMPTS})")
                    await self.device.connect()
                    await self.device.set_mode("manual")
                    await self.device.start_walking()
                    self._session_active = True
                    break
                except Exception as e:
                    logger.error(f"Connection attempt {attempt + 1} failed: {str(e)}")
                    if attempt < self.MAX_RECONNECT_ATTEMPTS - 1:
                        await asyncio.sleep(self.RECONNECT_DELAY)
                    else:
                        raise Exception("Failed to connect after multiple attempts")

            # Start metrics streaming
            self._stream_task = asyncio.create_task(self._stream_session_data())
            return self.current_session

        except Exception as e:
            self._session_active = False
            logger.error(f"Failed to start session: {str(e)}")
            # Cleanup if session was created but device connection failed
            if self.current_session:
                await self._cleanup_failed_session(self.current_session.id)
            raise

    async def _cleanup_failed_session(self, session_id: int):
        """Clean up a failed session from the database"""
        try:
            query = "DELETE FROM exercise_sessions WHERE id = %s"
            self.db.execute_query(query, (session_id,))
            logger.info(f"Cleaned up failed session {session_id}")
        except Exception as e:
            logger.error(f"Failed to cleanup session {session_id}: {str(e)}")

    async def _stream_session_data(self):
        """Stream real-time data with error handling"""
        try:
            while self._session_active:
                try:
                    status = await self.device.get_fast_status()
                    self._last_metrics = StreamMetrics(
                        distance_km=status['distance'],
                        steps=status['steps'],
                        duration_seconds=status['time'],
                        speed=status['speed'],
                        belt_state=status['belt_state']
                    )
                    await self._update_session_in_db()
                except Exception as e:
                    logger.error(f"Error in metrics stream: {str(e)}")
                    if "Unreachable" in str(e):
                        await self._attempt_reconnect()

                await asyncio.sleep(self._metrics_update_interval)

        except asyncio.CancelledError:
            logger.info("Session stream cancelled")
        except Exception as e:
            logger.error(f"Fatal error in session stream: {str(e)}")
            self._session_active = False
            raise

    async def _attempt_reconnect(self):
        """Attempt to reconnect to the device"""
        for attempt in range(self.MAX_RECONNECT_ATTEMPTS):
            try:
                await self.device.disconnect()
                await asyncio.sleep(self.RECONNECT_DELAY)
                await self.device.connect()
                logger.info("Successfully reconnected to device")
                return
            except Exception as e:
                logger.error(f"Reconnection attempt {attempt + 1} failed: {str(e)}")

        self._session_active = False
        raise Exception("Failed to reconnect to device")

    async def _update_session_in_db(self):
        """Update session in database"""
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
            logger.error(f"Failed to update session in DB: {e}")

    async def get_current_metrics(self) -> Optional[StreamMetrics]:
        """Get current session metrics"""
        return self._last_metrics

    async def end_session(self) -> ExerciseSession:
        """End current session and cleanup"""
        try:
            if not self.current_session:
                raise ValueError("No active session found")

            # Stop streaming
            self._session_active = False
            if self._stream_task:
                self._stream_task.cancel()
                await asyncio.wait_for(self._stream_task, timeout=5.0)

            # Stop the walking pad (this will also disconnect)
            await self.device.stop_walking()

            # Final session update
            end_time = datetime.now(timezone.utc)
            if self._last_metrics:
                # Get user weight for calories
                user_result = self.db.execute_query(
                    "SELECT weight_kg FROM users WHERE id = %s",
                    (self.current_session.user_id,)
                )
                user_weight = user_result[0]['weight_kg'] if user_result else 70

                calories = calculate_calories(
                    distance_km=self._last_metrics.distance_km,
                    duration_minutes=self._last_metrics.duration_seconds / 60,
                    weight_kg=user_weight
                )

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
                    final_session = ExerciseSession.from_db_row(result[0])
                    self.current_session = None
                    self._last_metrics = None
                    return final_session

            raise Exception("Failed to update final session data")

        except Exception as e:
            logger.error(f"Error ending session: {e}")
            raise

# Create singleton instance
exercise_stream_service = ExerciseStreamService()