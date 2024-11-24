# !/usr/bin/env python
"""
Emergency stop utility for WalkingPad
Immediately stops the walking pad and sets it to standby mode
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from api.services.device import device_service
from api.utils.logger import get_logger
from api.models.device import DeviceMode

logger = get_logger()


class EmergencyStop:
    """Emergency stop handler"""

    def __init__(self):
        """Initialize emergency stop handler"""
        self.device = device_service

    async def execute_stop(self):
        """Execute emergency stop sequence"""
        try:
            logger.info("Initiating emergency stop...")

            # Get current status
            status = await self.device.get_status()
            logger.info(f"Current status: {status['mode']} ({status['belt_state']})")

            # Stop the belt
            logger.info("Stopping belt...")
            await self.device.stop()

            # Switch to standby mode
            logger.info("Setting to standby mode...")
            await self.device.set_mode(DeviceMode.STANDBY)

            # Verify status
            final_status = await self.device.get_status()
            if final_status['belt_state'] == 'standby':
                logger.info("Emergency stop completed successfully")
            else:
                logger.error("Failed to confirm standby status")

        except Exception as e:
            logger.error(f"Emergency stop failed: {e}")
            raise


async def main():
    """Main execution function"""
    stopper = EmergencyStop()
    try:
        await stopper.execute_stop()
    except KeyboardInterrupt:
        logger.warning("\nOperation interrupted by user")
    except Exception as e:
        logger.error(f"Emergency stop failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    loop.close()
