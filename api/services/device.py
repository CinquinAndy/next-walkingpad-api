"""
WalkingPad device service
"""
import asyncio
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

        # Set up status handler
        self.last_status = {
            "steps": None,
            "distance": None,
            "time": None
        }
        self.controller.handler_last_status = self._on_new_status

    def _on_new_status(self, sender, record):
        """Handle new status updates from device"""
        distance_in_km = record.dist / 100
        print(f"Distance: {distance_in_km}km")
        print(f"Time: {record.time} seconds")
        print(f"Steps: {record.steps}")

        self.last_status.update({
            "steps": record.steps,
            "distance": distance_in_km,
            "time": record.time
        })

    async def start_walking(self, initial_speed: int = None):
        """Start the walking pad"""
        logger.info(f"Starting walking pad with initial speed: {initial_speed}")
        try:
            await self.connect()

            # Set initial speed if provided
            if initial_speed is not None:
                # Convert speed to the format expected by the device (multiply by 10)
                device_speed = initial_speed * 10
                await self.controller.change_speed(device_speed)
                await asyncio.sleep(self.minimal_cmd_space)

            # Start the belt
            await self.controller.start_belt()
            await asyncio.sleep(self.minimal_cmd_space)

            logger.info("Walking pad started successfully")
            return {"success": True, "status": "running"}

        except Exception as e:
            logger.error(f"Failed to start walking pad: {e}")
            raise
        finally:
            await self.disconnect()

    async def stop_walking(self):
        """Stop the walking pad"""
        logger.info("Stopping walking pad")
        try:
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

    async def set_speed(self, speed: int):
        """Set the walking pad speed"""
        logger.info(f"Setting speed to: {speed}")
        try:
            await self.connect()
            await self.controller.change_speed(speed)  # Convert to device speed
            await asyncio.sleep(self.minimal_cmd_space)

            logger.info(f"Speed set successfully to {speed}")
            return {"success": True, "current_speed": speed}

        except Exception as e:
            logger.error(f"Failed to set speed: {e}")
            raise
        finally:
            await self.disconnect()

    async def set_mode(self, mode: str):
        """Set the walking pad mode"""
        logger.info(f"Setting mode to: {mode}")
        try:
            await self.connect()

            # Convert string mode to controller mode
            if mode == "manual":
                mode_value = WalkingPad.MODE_MANUAL
            elif mode == "auto":
                mode_value = WalkingPad.MODE_AUTOMAT
            elif mode == "standby":
                mode_value = WalkingPad.MODE_STANDBY
            else:
                raise ValueError(f"Invalid mode: {mode}")

            await self.controller.switch_mode(mode_value)
            await asyncio.sleep(self.minimal_cmd_space)

            logger.info(f"Mode set successfully to {mode}")
            return {"success": True, "mode": mode}

        except Exception as e:
            logger.error(f"Failed to set mode: {e}")
            raise
        finally:
            await self.disconnect()

    async def calibrate(self):
        """Calibrate the walking pad"""
        logger.info("Starting calibration")
        try:
            await self.connect()
            await self.controller.calibrate()
            await asyncio.sleep(self.minimal_cmd_space)

            logger.info("Calibration completed successfully")
            return {"success": True, "message": "Calibration completed"}

        except Exception as e:
            logger.error(f"Calibration failed: {e}")
            raise
        finally:
            await self.disconnect()


    async def connect(self):
        """Connect to the WalkingPad device"""
        logger.info("[try to connect]")
        address = Config.get_device_address()
        print(f"Connecting to {address}")
        await self.controller.run(address)
        await asyncio.sleep(self.minimal_cmd_space)

    async def disconnect(self):
        """Disconnect from device"""
        await self.controller.disconnect()
        await asyncio.sleep(self.minimal_cmd_space)

    async def get_status(self):
        """Get current device status"""
        try:
            await self.connect()
            logger.info("[service device] - after connect")
            await self.controller.ask_stats()
            await asyncio.sleep(self.minimal_cmd_space)

            stats = self.controller.last_status
            return {
                "mode": self._get_mode_string(stats.manual_mode),
                "belt_state": self._get_belt_state_string(stats.belt_state),
                "distance": stats.dist / 100,
                "time": stats.time,
                "steps": stats.steps,
                "speed": stats.speed / 10
            }
        finally:
            await self.disconnect()

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
