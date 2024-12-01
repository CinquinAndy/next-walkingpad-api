"""
Connection and initialization service for WalkingPad
"""
from typing import Tuple, Dict, Any, Optional
import asyncio
from api.services.device import device_service
from api.services.security import ExerciseSecurityService
from api.services.database import DatabaseService
from api.utils.logger import get_logger
from ph4_walkingpad.pad import Scanner

logger = get_logger()


class InitializationService:
    """Service handling device initialization and connection"""

    def __init__(self):
        """Initialize the service"""
        self.device = device_service
        self.db = DatabaseService()
        self.security = ExerciseSecurityService(self.db, self.device)
        self.scanner = Scanner()

    async def scan_for_device(self, timeout: int = 10) -> Optional[Dict[str, Any]]:
        """
        Scan for WalkingPad devices

        Args:
            timeout: Scan duration in seconds

        Returns:
            Dict with device info or None if not found
        """
        try:
            logger.info(f"Scanning for WalkingPad devices (timeout: {timeout}s)")
            devices = await self.scanner.scan(timeout=timeout)

            for device in devices:
                device_name = device.name or "Unknown"
                if "walkingpad" in device_name.lower():
                    logger.info(f"Found WalkingPad: {device_name} ({device.address})")
                    return {
                        'name': device_name,
                        'address': device.address,
                        'rssi': device.rssi
                    }

            logger.warning("No WalkingPad devices found")
            return None

        except Exception as e:
            logger.error(f"Scan failed: {e}")
            raise

    async def initialize_device(self) -> Tuple[bool, Dict[str, Any]]:
        """
        Complete device initialization sequence

        Returns:
            Tuple[success: bool, response: Dict]
        """
        try:
            # 1. Scan for device
            device_info = await self.scan_for_device()
            if not device_info:
                return False, {
                    'status': 'error',
                    'message': 'No WalkingPad device found',
                    'step': 'scan'
                }

            # 2. Verify and clean device state
            logger.info("Verifying device state...")
            is_ready, error_message = await self.security.check_and_clean_state()

            if not is_ready:
                return False, {
                    'status': 'error',
                    'message': error_message,
                    'step': 'state_check',
                    'device_info': device_info
                }

            # 3. Set initial device configuration
            try:
                await self.device.connect()

                # Set to manual mode
                await self.device.controller.switch_mode(1)  # 1 = manual mode
                await asyncio.sleep(self.device.minimal_cmd_space)

                # Get final status
                await self.device.controller.ask_stats()
                await asyncio.sleep(self.device.minimal_cmd_space)
                final_status = self.device.controller.last_status

            except Exception as e:
                logger.error(f"Device configuration failed: {e}")
                return False, {
                    'status': 'error',
                    'message': f'Device configuration failed: {str(e)}',
                    'step': 'configuration',
                    'device_info': device_info
                }
            finally:
                await self.device.disconnect()

            # 4. Return success response
            return True, {
                'status': 'success',
                'message': 'Device initialized successfully',
                'device_info': device_info,
                'device_status': {
                    'mode': 'manual',
                    'speed': final_status.speed / 10 if final_status else 0,
                    'ready': True
                }
            }

        except Exception as e:
            logger.error(f"Initialization failed: {e}")
            return False, {
                'status': 'error',
                'message': str(e),
                'step': 'unknown'
            }


# Create singleton instance
initialization_service = InitializationService()