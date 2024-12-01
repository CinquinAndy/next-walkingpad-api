"""
DeviceService module provides a high-level interface to control a WalkingPad treadmill.
Features:
- Automatic connection management
- Status tracking and caching
- Error handling and retries
- Comprehensive device control (speed, mode, preferences)
- Real-time status updates
"""

import asyncio
from functools import wraps
from typing import Dict, Callable, Any

from ph4_walkingpad import pad
from ph4_walkingpad.pad import WalkingPad, Controller
from ph4_walkingpad.utils import setup_logging

from api.config.config import Config
from api.utils.logger import logger


def ensure_connection(disconnect_after: bool = False):
    """
    Decorator that manages device connectivity for method calls.
    Ensures the device is connected before executing the decorated method and handles
    disconnection based on the specified policy.

    Args:
        disconnect_after (bool): If True, forces disconnection after method execution
                               regardless of initial connection state

    Example:
        @ensure_connection(disconnect_after=True)
        async def some_method(self):
            # Method code here
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(self, *args, **kwargs) -> Any:
            was_connected = self.is_connected

            if not was_connected:
                await self.connect()

            try:
                result = await func(self, *args, **kwargs)
                return result
            finally:
                if not was_connected or disconnect_after:
                    await self.disconnect()

        return wrapper
    return decorator


class DeviceService:
    """
    Service class for managing WalkingPad device operations with optimized connection handling
    and comprehensive status tracking.
    """

    def __init__(self):
        """
        Initialize DeviceService with default configuration and status tracking.
        Sets up logging, controller, and status cache.
        """
        self.log = setup_logging()
        pad.logger = self.log
        self.controller = Controller()
        self.minimal_cmd_space = Config.MINIMAL_CMD_SPACE
        self.is_connected = False

        # Initialize status cache
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
        Callback handler for device status updates.
        Updates internal status cache with latest device values.

        Args:
            sender: Source of the status update
            record: Status data from device
        """
        if record:
            self._last_status.update({
                "mode": self._get_mode_string(record.mode),
                "belt_state": self._get_belt_state_string(record.state),
                "speed": record.speed / 10,
                "distance": record.dist / 100,
                "steps": record.steps,
                "time": record.time
            })

            logger.debug(f"Status updated: {self._last_status}")

    @ensure_connection(disconnect_after=False)
    async def get_fast_status(self) -> Dict:
        """
        Quickly retrieve device status from cache with minimal device communication.

        Returns:
            Dict: Current cached device status

        Raises:
            Exception: If status retrieval fails
        """
        try:
            await self.controller.ask_stats()
            await asyncio.sleep(self.minimal_cmd_space)

            if all(v is None for v in self._last_status.values()):
                logger.warning("Invalid status received, requesting new status")
                await self.controller.ask_stats()
                await asyncio.sleep(self.minimal_cmd_space)

            return self._last_status.copy()
        except Exception as e:
            logger.error(f"Error getting fast status: {e}")
            raise

    @ensure_connection(disconnect_after=False)
    async def get_status(self) -> Dict:
        """
        Retrieves comprehensive device status information.
        Performs a fresh query to the device and updates internal cache.

        Returns:
            Dict containing:
                - mode (str): Current operation mode ('manual', 'auto', 'standby')
                - belt_state (str): Current belt state ('idle', 'running', 'standby')
                - speed (float): Current speed in km/h
                - distance (float): Total distance covered in km
                - steps (int): Total step count
                - time (int): Total running time in seconds

        Raises:
            RuntimeError: If communication with device fails
        """
        logger.debug("Getting device status")
        try:
            await self.controller.ask_stats()
            await asyncio.sleep(self.minimal_cmd_space)
            return self._last_status.copy()
        except Exception as e:
            logger.error(f"Failed to get device status: {e}")
            raise RuntimeError("Failed to read device status") from e

    @ensure_connection(disconnect_after=False)
    async def start_walking(self, initial_speed: int = None):
        """
        Start the walking pad with optional initial speed setting.

        Args:
            initial_speed (int, optional): Initial speed to set in km/h

        Returns:
            dict: Operation status and confirmation

        Raises:
            Exception: If start operation fails
        """
        logger.info(f"Starting walking pad with initial speed: {initial_speed}")
        try:
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
            raise

    @ensure_connection(disconnect_after=True)
    async def stop_walking(self):
        """
        Stop the walking pad and disconnect from device.

        Returns:
            dict: Operation status and confirmation

        Raises:
            Exception: If stop operation fails
        """
        logger.info("Stopping walking pad")
        await self.controller.stop_belt()
        await asyncio.sleep(self.minimal_cmd_space)
        logger.info("Walking pad stopped successfully")
        return {"success": True, "status": "stopped"}

    async def connect(self):
        """
        Establish connection to the WalkingPad device.
        Only connects if not already connected.
        """
        if not self.is_connected:
            logger.info("Connecting to device...")
            address = Config.get_device_address()
            await self.controller.run(address)
            await asyncio.sleep(self.minimal_cmd_space)
            self.is_connected = True
            logger.info("Device connected successfully")

    async def disconnect(self):
        """
        Safely disconnect from the device if connected.
        """
        if self.is_connected:
            await self.controller.disconnect()
            await asyncio.sleep(self.minimal_cmd_space)
            self.is_connected = False
            logger.info("Device disconnected")

    @ensure_connection(disconnect_after=True)
    async def set_mode(self, mode: str):
        """
        Set the operation mode of the device.

        Args:
            mode (str): Desired mode ('manual', 'auto', 'standby')

        Returns:
            dict: Operation status and confirmation

        Raises:
            ValueError: If invalid mode specified
            Exception: If mode change fails
        """
        logger.info(f"Setting mode to: {mode}")
        try:
            mode_value = {
                "manual": WalkingPad.MODE_MANUAL,
                "auto": WalkingPad.MODE_AUTOMAT,
                "standby": WalkingPad.MODE_STANDBY
            }.get(mode)

            if mode_value is None:
                raise ValueError(f"Invalid mode: {mode}")

            await self.controller.switch_mode(mode_value)
            await asyncio.sleep(self.minimal_cmd_space)
            return {"success": True, "mode": mode}
        except Exception as e:
            logger.error(f"Failed to set mode: {e}")
            raise

    @ensure_connection(disconnect_after=True)
    async def set_speed(self, speed: int):
        """
        Set the walking pad speed.

        Args:
            speed (int): Desired speed in km/h

        Returns:
            dict: Operation status and current speed

        Raises:
            Exception: If speed change fails
        """
        logger.info(f"Setting speed to: {speed}")
        await self.controller.change_speed(speed)
        await asyncio.sleep(self.minimal_cmd_space)
        return {"success": True, "current_speed": speed}

    @ensure_connection(disconnect_after=True)
    async def update_preferences(self, max_speed: float, start_speed: float,
                               sensitivity: int, child_lock: bool,
                               units_miles: bool) -> dict:
        """
        Update device preferences with retry mechanism for reliability.

        Args:
            max_speed (float): Maximum allowed speed in km/h
            start_speed (float): Default starting speed in km/h
            sensitivity (int): Belt sensitivity level (1-3)
            child_lock (bool): Enable/disable child lock
            units_miles (bool): True for imperial units, False for metric

        Returns:
            dict: Status and confirmation of updated preferences

        Raises:
            Exception: If preferences cannot be set after maximum retry attempts
        """
        logger.info(f"Updating device preferences: max_speed={max_speed}, "
                   f"start_speed={start_speed}, sensitivity={sensitivity}, "
                   f"child_lock={child_lock}, units_miles={units_miles}")

        max_retries = 3
        retry_delay = 2

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
                    if attempt == max_retries - 1:
                        raise Exception(f"Failed to set {pref_name} after {max_retries} attempts")

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

    @staticmethod
    def _get_mode_string(mode):
        """
        Convert internal mode value to human-readable string.

        Args:
            mode: Internal mode value from device

        Returns:
            str: Human-readable mode string
        """
        if mode == WalkingPad.MODE_STANDBY:
            return "standby"
        elif mode == WalkingPad.MODE_MANUAL:
            return "manual"
        elif mode == WalkingPad.MODE_AUTOMAT:
            return "auto"
        return "unknown"

    @staticmethod
    def _get_belt_state_string(state):
        """
        Convert internal belt state to human-readable string.

        Args:
            state: Internal state value from device

        Returns:
            str: Human-readable belt state string
        """
        if state == 5:
            return "standby"
        elif state == 0:
            return "idle"
        elif state == 1:
            return "running"
        elif state == 2:
            return "running"
        elif state >= 7:
            return "starting"
        return "unknown"


# Create singleton instance
device_service = DeviceService()
