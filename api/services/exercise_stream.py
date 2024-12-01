"""
api/services/exercise_stream.py
Exercise streaming service optimized for real-time data collection
"""
import asyncio
from datetime import datetime, timezone
from dataclasses import dataclass
from typing import Optional

from api.models.exercise import ExerciseSession
from api.services.database import DatabaseService
from api.services.device import device_service
from api.utils.helpers import calculate_calories
from api.utils.logger import get_logger

logger = get_logger()

@dataclass
class StreamMetrics:
    """Real-time session metrics"""
    distance_km: float
    steps: int
    duration_seconds: int
    speed: float
    calories: Optional[int] = None
    belt_state: Optional[str] = None

class ExerciseStreamService:
    """Service for managing exercise sessions with optimized streaming"""

    def __init__(self):
        """Initialize streaming service"""
        self.db = DatabaseService()
        self.device = device_service
        self.current_session: Optional[ExerciseSession] = None
        self._session_active = False
        self._metrics_update_interval = 1.0  # seconds
        self._last_metrics: Optional[StreamMetrics] = None
        self._stream_task: Optional[asyncio.Task] = None

    async def start_session(self) -> ExerciseSession:
        """Start new exercise session with streaming"""
        try:
            # Connect to device first (will stay connected during session)
            await self.device.connect()

            # Set device to manual mode
            await self.device.set_mode("manual")

            # Create session in database
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

            # Start the walking pad
            await self.device.start_walking()
            self._session_active = True

            # Start metrics streaming
            self._stream_task = asyncio.create_task(self._stream_session_data())

            return self.current_session

        except Exception as e:
            self._session_active = False
            await self.device.disconnect()
            logger.error(f"Failed to start session: {e}")
            raise

    async def _stream_session_data(self):
        """Stream real-time data using fast status"""
        try:
            while self._session_active:
                # Get status using fast method
                status = await self.device.get_fast_status()

                # Update metrics
                self._last_metrics = StreamMetrics(
                    distance_km=status['distance'],
                    steps=status['steps'],
                    duration_seconds=status['time'],
                    speed=status['speed'],
                    belt_state=status['belt_state']
                )

                # Periodic database update
                await self._update_session_in_db()

                await asyncio.sleep(self._metrics_update_interval)

        except asyncio.CancelledError:
            logger.info("Session stream cancelled")
        except Exception as e:
            logger.error(f"Error in session stream: {e}")
            self._session_active = False
            raise

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