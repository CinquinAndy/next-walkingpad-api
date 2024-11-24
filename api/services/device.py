"""
WalkingPad device service
"""
import asyncio
from ph4_walkingpad import pad
from ph4_walkingpad.pad import WalkingPad, Controller
from ph4_walkingpad.utils import setup_logging
from api.config.config import Config


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

    async def connect(self):
        """Connect to the WalkingPad device"""
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
