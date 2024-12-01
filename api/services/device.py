"""
WalkingPad device service with optimized connection handling and status tracking
"""
import asyncio
from typing import Dict

from ph4_walkingpad import pad
from ph4_walkingpad.pad import WalkingPad, Controller
from ph4_walkingpad.utils import setup_logging

from api.config.config import Config
from api.utils.logger import logger


class DeviceService:
    """Service for interacting with WalkingPad device"""

    def __init__(self):
        """Initialize the device service"""
        self.log = setup_logging()
        pad.logger = self.log
        self.controller = Controller()
        self.minimal_cmd_space = Config.MINIMAL_CMD_SPACE
        self.is_connected = False

        # Enhanced status tracking
        self._last_status = {
            "mode": None,
            "belt_state": None,
            "speed": 0,
            "distance": 0,
            "steps": 0,
            "time": 0
        }

        self.controller.handler_last_status = self._on_new_status

    def _on_new_status(self, sender, record):
        """
        Handle new status updates from device.
        Updates internal status cache with latest values.
        """
        # Update internal status cache with converted values
        self._last_status.update({
            "mode": self._get_mode_string(record.manual_mode),
            "belt_state": self._get_belt_state_string(record.belt_state),
            "speed": record.speed / 10,
            "distance": record.dist / 100,
            "steps": record.steps,
            "time": record.time
        })

        logger.debug(f"Status updated - Distance: {self._last_status['distance']}km, "
                    f"Steps: {self._last_status['steps']}, "
                    f"Time: {self._last_status['time']} seconds")

    async def get_fast_status(self) -> Dict:
        """
        Get current device status without reconnecting.
        Must be used only when device is already connected.

        Returns:
            Dict: Current device status

        Raises:
            RuntimeError: If device is not connected
        """
        if not self.is_connected:
            raise RuntimeError("Device must be connected to use fast status")

        try:
            await self.controller.ask_stats()
            await asyncio.sleep(self.minimal_cmd_space)
            return self._last_status.copy()
        except Exception as e:
            logger.error(f"Fast status check failed: {e}")
            raise

    async def start_walking(self, initial_speed: int = None):
        """Start the walking pad"""
        logger.info(f"Starting walking pad with initial speed: {initial_speed}")
        try:
            if not self.is_connected:
                await self.connect()

            if initial_speed is not None:
                device_speed = initial_speed * 10
                await self.controller.change_speed(device_speed)
                await asyncio.sleep(self.minimal_cmd_space)

            await self.controller.start_belt()
            await asyncio.sleep(self.minimal_cmd_space)

            logger.info("Walking pad started successfully")
            return {"success": True, "status": "running"}

        except Exception as e:
            logger.error(f"Failed to start walking pad: {e}")
            await self.disconnect()  # Disconnect only on error
            raise

    async def stop_walking(self):
        """Stop the walking pad"""
        logger.info("Stopping walking pad")
        try:
            if not self.is_connected:
                await self.connect()

            await self.controller.stop_belt()
            await asyncio.sleep(self.minimal_cmd_space)

            logger.info("Walking pad stopped successfully")
            return {"success": True, "status": "stopped"}

        except Exception as e:
            logger.error(f"Failed to stop walking pad: {e}")
            raise
        finally:
            await self.disconnect()

    async def connect(self):
        """Connect to the WalkingPad device"""
        if not self.is_connected:
            logger.info("Connecting to device...")
            address = Config.get_device_address()
            await self.controller.run(address)
            await asyncio.sleep(self.minimal_cmd_space)
            self.is_connected = True
            logger.info("Device connected successfully")

    async def disconnect(self):
        """Disconnect from device"""
        if self.is_connected:
            await self.controller.disconnect()
            await asyncio.sleep(self.minimal_cmd_space)
            self.is_connected = False
            logger.info("Device disconnected")

    async def get_status(self):
        """
        Get current device status (with full connection cycle).
        Use get_fast_status() instead if device is already connected.
        """
        try:
            await self.connect()
            logger.info("Getting device status")
            status = await self.get_fast_status()
            return status
        finally:
            await self.disconnect()

    async def update_preferences(self, max_speed: float, start_speed: float,
                                 sensitivity: int, child_lock: bool,
                                 units_miles: bool) -> dict:
        """
        Update device preferences with retry mechanism
        """
        logger.info(f"Updating device preferences: max_speed={max_speed}, "
                    f"start_speed={start_speed}, sensitivity={sensitivity}, "
                    f"child_lock={child_lock}, units_miles={units_miles}")

        max_retries = 3
        retry_delay = 2  # seconds

        try:
            await self.connect()

            # Set all preferences in sequence with retries
            preferences_to_set = [
                ('max_speed', WalkingPad.PREFS_MAX_SPEED, int(max_speed * 10)),
                ('start_speed', WalkingPad.PREFS_START_SPEED, int(start_speed * 10)),
                ('sensitivity', WalkingPad.PREFS_SENSITIVITY, sensitivity),
                ('child_lock', WalkingPad.PREFS_CHILD_LOCK, int(child_lock)),
                ('units', WalkingPad.PREFS_UNITS, int(units_miles))
            ]

            for pref_name, pref_key, pref_value in preferences_to_set:
                for attempt in range(max_retries):
                    try:
                        logger.debug(f"Setting {pref_name} to: {pref_value} (attempt {attempt + 1}/{max_retries})")
                        await self.controller.set_pref_int(pref_key, pref_value)
                        await asyncio.sleep(self.minimal_cmd_space)
                        break
                    except Exception as e:
                        logger.warning(f"Attempt {attempt + 1} failed for {pref_name}: {e}")
                        if attempt < max_retries - 1:
                            # Reconnect and retry
                            await self.disconnect()
                            await asyncio.sleep(retry_delay)
                            await self.connect()
                        else:
                            raise Exception(f"Failed to set {pref_name} after {max_retries} attempts")

            logger.info("Device preferences updated successfully")

            # No need to verify status immediately as it might cause connection issues
            return {
                'success': True,
                'message': 'Preferences updated successfully',
                'data': {
                    'max_speed': max_speed,
                    'start_speed': start_speed,
                    'sensitivity': sensitivity,
                    'child_lock': child_lock,
                    'units_miles': units_miles
                }
            }

        except Exception as e:
            logger.error(f"Failed to update device preferences: {e}", exc_info=True)
            raise Exception(f"Failed to update device preferences: {str(e)}")
        finally:
            try:
                await self.disconnect()
            except Exception as e:
                logger.warning(f"Error during disconnect: {e}")

    @staticmethod
    def _get_mode_string(mode):
        """Convert mode value to string"""
        if mode == WalkingPad.MODE_STANDBY:
            return "standby"
        elif mode == WalkingPad.MODE_MANUAL:
            return "manual"
        elif mode == WalkingPad.MODE_AUTOMAT:
            return "auto"
        return "unknown"

    @staticmethod
    def _get_belt_state_string(state):
        """Convert belt state value to string"""
        if state == 5:
            return "standby"
        elif state == 0:
            return "idle"
        elif state == 1:
            return "running"
        elif state >= 7:
            return "starting"
        return "unknown"


# Create a singleton instance
device_service = DeviceService()
