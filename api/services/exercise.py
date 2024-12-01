"""
Enhanced exercise service with persistent device connection and efficient metrics handling
"""
import asyncio
from datetime import datetime, timezone
from typing import Optional, Dict
import threading

from api.models.exercise import ExerciseSession, ExerciseHistory, ExerciseStats
from api.services.database import DatabaseService
from api.services.device import device_service
from api.utils.helpers import calculate_calories
from api.utils.logger import get_logger

logger = get_logger()

class ExerciseService:
    """Service for managing exercise sessions with persistent device connection"""

    def __init__(self):
        """Initialize service with connection management"""
        self.db = DatabaseService()
        self.device = device_service
        self.current_session: Optional[ExerciseSession] = None
        self._last_device_metrics: Dict = {}
        self._metrics_lock = threading.Lock()
        self._connection_established = False
        self._last_metrics_update = 0
        self.METRICS_CACHE_DURATION = 0.5  # seconds

    async def ensure_device_connection(self):
        """Ensure device is connected, connecting if necessary"""
        if not self._connection_established:
            try:
                await self.device.connect()
                await self.device.set_mode("manual")
                self._connection_established = True
                logger.info("Device connection established")
            except Exception as e:
                logger.error(f"Failed to establish device connection: {e}")
                raise

    async def _get_device_metrics(self) -> Dict:
        """Get device metrics with caching and retry logic"""
        current_time = datetime.now().timestamp()

        # Return cached metrics if recent enough
        if (current_time - self._last_metrics_update) < self.METRICS_CACHE_DURATION:
            return self._last_device_metrics

        try:
            await self.ensure_device_connection()

            max_retries = 3
            for attempt in range(max_retries):
                try:
                    status = await self.device.get_status()
                    if status:
                        with self._metrics_lock:
                            self._last_device_metrics = {
                                'distance_km': float(status.get('distance', 0)),
                                'duration_seconds': int(status.get('time', 0)),
                                'steps': int(status.get('steps', 0)),
                                'speed': float(status.get('speed', 0))
                            }
                            self._last_metrics_update = current_time
                        return self._last_device_metrics
                except Exception as e:
                    logger.error(f"Metrics fetch attempt {attempt + 1} failed: {e}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(1)

            return self._last_device_metrics

        except Exception as e:
            logger.error(f"Failed to get device metrics: {e}")
            return self._last_device_metrics or {
                'distance_km': 0.0,
                'duration_seconds': 0,
                'steps': 0,
                'speed': 0.0
            }

    async def start_session(self) -> ExerciseSession:
        """Start new exercise session with persistent connection"""
        try:
            await self.ensure_device_connection()

            current_time = datetime.now(timezone.utc)
            query = """
                INSERT INTO exercise_sessions 
                (user_id, start_time, mode, steps, distance_km, duration_seconds, 
                 calories, average_speed, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING *
            """
            params = (1, current_time, 'manual', 0, 0.0, 0, 0, 0.0, current_time)

            result = self.db.execute_query(query, params)
            if not result:
                raise Exception("Failed to create session")

            self.current_session = ExerciseSession.from_db_row(result[0])
            await self.device.start_walking()

            logger.info(f"Started session: {self.current_session.id}")
            return self.current_session

        except Exception as e:
            logger.error(f"Failed to start session: {e}")
            await self._cleanup_on_error()
            raise

    async def end_session(self) -> ExerciseSession:
        """End current session while maintaining device connection"""
        try:
            if not self.current_session:
                raise ValueError("No active session found")

            # Get final metrics
            metrics = await self._get_device_metrics()
            await self.device.stop_walking()

            # Calculate final statistics
            end_time = datetime.now(timezone.utc)
            duration_seconds = metrics['duration_seconds']

            # Update session in database
            query = """
                UPDATE exercise_sessions 
                SET end_time = %s, steps = %s, distance_km = %s,
                    duration_seconds = %s, calories = %s, average_speed = %s,
                    updated_at = %s
                WHERE id = %s
                RETURNING *
            """
            params = (
                end_time, metrics['steps'], metrics['distance_km'],
                duration_seconds, self._calculate_calories(metrics),
                self._calculate_average_speed(metrics), end_time,
                self.current_session.id
            )

            result = self.db.execute_query(query, params)
            if not result:
                raise Exception("Failed to update session")

            session = ExerciseSession.from_db_row(result[0])
            self.current_session = None
            return session

        except Exception as e:
            logger.error(f"Error ending session: {e}")
            await self._cleanup_on_error()
            raise

    async def _cleanup_on_error(self):
        """Clean up resources on error"""
        try:
            await self.device.stop_walking()
        except Exception as e:
            logger.error(f"Cleanup error: {e}")

    def _calculate_calories(self, metrics: Dict) -> int:
        """Calculate calories burned based on metrics"""
        duration_minutes = metrics['duration_seconds'] / 60
        # Get user weight (default to 70kg if not found)
        user_weight = 70
        if self.current_session:
            result = self.db.execute_query(
                "SELECT weight_kg FROM users WHERE id = %s",
                (self.current_session.user_id,)
            )
            if result:
                user_weight = result[0]['weight_kg']

        return calculate_calories(
            distance_km=metrics['distance_km'],
            duration_minutes=duration_minutes,
            weight_kg=user_weight
        )

    def _calculate_average_speed(self, metrics: Dict) -> float:
        """Calculate average speed in km/h"""
        duration_hours = metrics['duration_seconds'] / 3600
        return metrics['distance_km'] / duration_hours if duration_hours > 0 else 0.0

# Create singleton instance
exercise_service = ExerciseService()