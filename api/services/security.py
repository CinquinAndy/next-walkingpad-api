"""
Exercise security service with improved session handling
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
        Check device state and clean if necessary.
        Now handles incomplete sessions without blocking new ones.
        """
        try:
            # 1. Check current device state
            current_status = await self.device.get_status()
            self.logger.info(f"Current device status: {current_status}")

            # 2. Force stop if device is still running
            if current_status.get('belt_state') not in ['idle', 'standby']:
                await self.device.stop_walking()
                self.logger.info("Force stopped the walking pad")
                await asyncio.sleep(self.device.minimal_cmd_space)

            # 3. Handle any incomplete sessions in background
            incomplete_sessions = await self._check_incomplete_sessions()
            if incomplete_sessions:
                # Auto-close old sessions but continue with new session
                await self._cleanup_incomplete_sessions(incomplete_sessions)
                self.logger.info(f"Auto-closed {len(incomplete_sessions)} old incomplete sessions")

            # 4. Check device memory for unsaved data
            last_stats = await self._get_last_device_stats()
            self.logger.info(f"Retrieved last device stats: {last_stats}")

            if last_stats and self._has_significant_data(last_stats):
                return False, "Unsaved session data found. Please check history and confirm before starting new session."

            # 5. Reset device state
            await self._reset_device_state()

            return True, None

        except Exception as e:
            self.logger.error(f"State check and cleanup failed: {e}", exc_info=True)
            return False, f"State cleanup failed: {str(e)}"

    async def _check_incomplete_sessions(self) -> list:
        """
        Find old incomplete sessions (more than 3 hours old)
        """
        query = """
            SELECT id, start_time 
            FROM exercise_sessions 
            WHERE end_time IS NULL
            AND start_time < NOW() - INTERVAL '3 hours'
            ORDER BY start_time DESC
        """
        return self.db.execute_query(query)

    async def _cleanup_incomplete_sessions(self, sessions: list):
        """
        Mark old sessions as ended with appropriate notes
        """
        try:
            for session in sessions:
                # Calculate a reasonable end time (30 minutes after start or current time)
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
            # Continue execution even if cleanup fails
            self.logger.info("Continuing despite cleanup failure")

    async def _get_last_device_stats(self) -> Optional[Dict]:
        """Retrieve last session statistics from device"""
        try:
            await self.device.connect()
            # Switch to manual mode (1)
            await self.device.controller.switch_mode(1)
            await asyncio.sleep(self.device.minimal_cmd_space)

            await self.device.controller.ask_stats()
            await asyncio.sleep(self.device.minimal_cmd_space)

            stats = self.device.controller.last_status
            if stats:
                return {
                    'distance': stats.dist / 100,
                    'steps': stats.steps,
                    'time': stats.time,
                    'timestamp': datetime.now(timezone.utc)
                }
            return None

        except Exception as e:
            self.logger.error(f"Failed to get device stats: {e}")
            return None
        finally:
            await self.device.disconnect()

    def _has_significant_data(self, stats: Dict) -> bool:
        """Check if stats represent significant activity"""
        return any([
            stats.get('distance', 0) > 0.05,  # More than 50m
            stats.get('steps', 0) > 50,       # More than 50 steps
            stats.get('time', 0) > 30         # More than 30 seconds
        ])

    async def _reset_device_state(self):
        """Reset device state through mode cycling"""
        try:
            await self.device.connect()

            # Cycle: Standby (0) -> Manual (1) -> Standby (0)
            for mode in [1]:
                await self.device.controller.switch_mode(mode)
                await asyncio.sleep(self.device.minimal_cmd_space)

            self.logger.info("Device state reset completed")

        except Exception as e:
            self.logger.error(f"Failed to reset device state: {e}")
            raise
        finally:
            await self.device.disconnect()