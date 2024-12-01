"""
Service for WalkingPad initialization and state preparation
"""
from typing import Tuple, Dict
import asyncio

from api.services.device import device_service
from api.utils.logger import get_logger

logger = get_logger()

class InitializationService:
    """Service for preparing WalkingPad device state"""

    def __init__(self):
        """Initialize service"""
        self.device = device_service

    async def prepare_device(self) -> Tuple[bool, Dict]:
        """
        Prepare device for use by ensuring clean state.

        Returns:
            Tuple[bool, Dict]: Success status and response details
        """
        try:
            logger.info("Starting device preparation")

            # 1. Connect to device
            await self.device.connect()

            try:
                # 2. Get initial status
                await self.device.controller.ask_stats()
                await asyncio.sleep(self.device.minimal_cmd_space)
                initial_stats = self.device.controller.last_status

                if not initial_stats:
                    return False, {
                        'status': 'error',
                        'message': 'Could not read device status'
                    }

                # 3. Check if device has unsaved data
                has_significant_data = (
                    initial_stats.dist > 5 or  # More than 5cm
                    initial_stats.steps > 50 or # More than 50 steps
                    initial_stats.time > 30     # More than 30 seconds
                )

                if has_significant_data:
                    logger.warning("Found unsaved data in device memory")
                    return False, {
                        'status': 'error',
                        'message': 'Device has unsaved data. Please check history first.',
                        'data': {
                            'distance': initial_stats.dist / 100,
                            'steps': initial_stats.steps,
                            'time': initial_stats.time
                        }
                    }

                # 4. Set to manual mode and stop
                await self.device.controller.stop_belt()
                await asyncio.sleep(self.device.minimal_cmd_space)

                await self.device.controller.switch_mode(1)  # Set to manual mode
                await asyncio.sleep(self.device.minimal_cmd_space)

                # 5. Get final status
                await self.device.controller.ask_stats()
                await asyncio.sleep(self.device.minimal_cmd_space)
                final_stats = self.device.controller.last_status

                return True, {
                    'status': 'success',
                    'message': 'Device ready for use',
                    'device_status': {
                        'mode': 'manual',
                        'belt_state': self.device._get_belt_state_string(final_stats.belt_state),
                        'speed': final_stats.speed / 10
                    }
                }

            finally:
                # Always disconnect
                await self.device.disconnect()

        except Exception as e:
            logger.error(f"Device preparation failed: {e}")
            return False, {
                'status': 'error',
                'message': str(e)
            }

# Create singleton instance
initialization_service = InitializationService()