"""
Optimized exercise security service with minimal device connections
"""
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple, Dict
import asyncio
from api.utils.logger import get_logger

class ExerciseSecurityService:
    """Service for managing exercise session security checks and cleanup"""

    def __init__(self, db_service, device_service):
        """Initialize security service"""
        self.db = db_service
        self.device = device_service
        self.logger = get_logger()

    async def check_and_clean_state(self) -> Tuple[bool, Optional[str]]:
        """
        Optimized state check and cleanup with minimal device connections.
        Handles all device operations in a single connection session.
        """
        try:
            # 1. Handle any incomplete sessions in background (db only, no device connection)
            incomplete_sessions = await self._check_incomplete_sessions()
            if incomplete_sessions:
                await self._cleanup_incomplete_sessions(incomplete_sessions)
                self.logger.info(f"Auto-closed {len(incomplete_sessions)} old incomplete sessions")

            # 2. Single device connection for all operations
            try:
                await self.device.connect()

                # Get initial status
                await self.device.controller.ask_stats()
                await asyncio.sleep(self.device.minimal_cmd_space)
                initial_stats = self.device.controller.last_status

                # Check for significant data
                if initial_stats and self._has_significant_data({
                    'distance': initial_stats.dist / 100,
                    'steps': initial_stats.steps,
                    'time': initial_stats.time
                }):
                    self.logger.warning("Found unsaved data in device memory")
                    return False, "Unsaved session data found. Please check history first."

                # Set to manual mode and prepare for operation
                await self.device.controller.switch_mode(1)  # Set to manual
                await asyncio.sleep(self.device.minimal_cmd_space)

                # Final status check
                await self.device.controller.ask_stats()
                await asyncio.sleep(self.device.minimal_cmd_space)

                self.logger.info("Device prepared and ready for new session")
                return True, None

            except Exception as e:
                self.logger.error(f"Device communication error: {e}")
                return False, f"Device communication failed: {str(e)}"
            finally:
                await self.device.disconnect()

        except Exception as e:
            self.logger.error(f"State check failed: {e}", exc_info=True)
            return False, f"State check failed: {str(e)}"

    def _has_significant_data(self, stats: Dict) -> bool:
        """Check if stats represent significant activity"""
        return any([
            stats.get('distance', 0) > 0.05,  # More than 50m
            stats.get('steps', 0) > 50,       # More than 50 steps
            stats.get('time', 0) > 30         # More than 30 seconds
        ])

    async def _check_incomplete_sessions(self) -> list:
        """Find old incomplete sessions (more than 3 hours old)"""
        query = """
            SELECT id, start_time 
            FROM exercise_sessions 
            WHERE end_time IS NULL
            AND start_time < NOW() - INTERVAL '3 hours'
            ORDER BY start_time DESC
        """
        return self.db.execute_query(query)

    async def _cleanup_incomplete_sessions(self, sessions: list):
        """Mark old sessions as ended with appropriate notes"""
        try:
            for session in sessions:
                start_time = session['start_time']
                estimated_end = min(
                    start_time + timedelta(minutes=30),
                    datetime.now(timezone.utc)
                )

                query = """
                    UPDATE exercise_sessions 
                    SET 
                        end_time = %s,
                        updated_at = NOW(),
                        notes = 'Auto-closed by system - Session was incomplete',
                        duration_seconds = EXTRACT(EPOCH FROM (%s - start_time))
                    WHERE id = %s
                """
                self.db.execute_query(query, (estimated_end, estimated_end, session['id']))
                self.logger.info(f"Auto-closed incomplete session {session['id']}")

        except Exception as e:
            self.logger.error(f"Failed to cleanup sessions: {e}")
            self.logger.info("Continuing despite cleanup failure")