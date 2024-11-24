"""
Exercise security service for safety checks and validation
"""
from typing import Optional, Tuple

from api.utils.logger import get_logger


class ExerciseSecurityService:
    """Service for managing exercise session security checks"""

    def __init__(self, db_service, device_service):
        """Initialize security service"""
        self.db = db_service
        self.device = device_service
        self.logger = get_logger()

    async def check_session_safety(self) -> Tuple[bool, Optional[str]]:
        """
        Perform safety checks before starting a new session

        Returns:
            Tuple[bool, Optional[str]]: (is_safe, error_message)
        """
        try:
            # Check 1: Verify device is stopped
            device_status = await self.device.get_status()
            if device_status.get('belt_state') not in ['idle', 'standby']:
                self.logger.warning("Attempted to start session while belt was moving")
                return False, "Walking pad must be stopped before starting a new session"

            # Check 2: Look for any uncompleted sessions
            incomplete_sessions = await self._check_incomplete_sessions()
            if incomplete_sessions:
                self.logger.warning(f"Found {len(incomplete_sessions)} incomplete sessions")
                return False, "There are incomplete sessions. Please end the current session first."

            # Check 3: Look for unsaved device data
            has_unsaved_data = await self._check_unsaved_data()
            if has_unsaved_data:
                self.logger.warning("Found unsaved data in device memory")
                return False, "Found unsaved exercise data. Please save or clear device data first."

            return True, None

        except Exception as e:
            self.logger.error(f"Session safety check failed: {e}", exc_info=True)
            return False, f"Safety check failed: {str(e)}"

    async def _check_incomplete_sessions(self) -> list:
        """Check for sessions without end_time"""
        try:
            query = """
                SELECT id, start_time 
                FROM exercise_sessions 
                WHERE end_time IS NULL
                ORDER BY start_time DESC
            """
            return self.db.execute_query(query)
        except Exception as e:
            self.logger.error(f"Failed to check incomplete sessions: {e}")
            raise

    async def _check_unsaved_data(self) -> bool:
        """
        Check if device has unsaved exercise data
        Returns True if unsaved data found
        """
        try:
            device_status = await self.device.get_status()
            # Check if there's significant unrecorded activity
            return (
                    device_status.get('distance', 0) > 0.1 or  # More than 100m
                    device_status.get('steps', 0) > 100 or  # More than 100 steps
                    device_status.get('time', 0) > 60  # More than 1 minute
            )
        except Exception as e:
            self.logger.error(f"Failed to check device data: {e}")
            raise