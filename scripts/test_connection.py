# !/usr/bin/env python
"""
Connection test utility for WalkingPad
Tests basic device connectivity and functionality
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


class ConnectionTester:
    """WalkingPad connection tester"""

    def __init__(self):
        """Initialize connection tester"""
        self.device = device_service

    async def run_tests(self):
        """Run connection test sequence"""
        try:
            logger.info("Starting connection tests...")

            # Test 1: Get Status
            logger.info("\n1. Testing status retrieval...")
            status = await self.device.get_status()
            logger.info(f"  Status: {status}")

            # Test 2: Mode Switch
            logger.info("\n2. Testing mode switching...")
            logger.info("  Setting to standby...")
            await self.device.set_mode(DeviceMode.STANDBY)
            await asyncio.sleep(1)

            logger.info("  Setting to manual...")
            await self.device.set_mode(DeviceMode.MANUAL)
            await asyncio.sleep(1)

            logger.info("  Returning to standby...")
            await self.device.set_mode(DeviceMode.STANDBY)

            # Test 3: Preferences
            logger.info("\n3. Testing preferences retrieval...")
            prefs = await self.device.get_preferences()
            logger.info(f"  Preferences: {prefs}")

            logger.info("\nAll tests completed successfully!")

        except Exception as e:
            logger.error(f"Test failed: {e}")
            raise


async def main():
    """Main execution function"""
    tester = ConnectionTester()
    try:
        await tester.run_tests()
    except KeyboardInterrupt:
        logger.warning("\nTests interrupted by user")
    except Exception as e:
        logger.error(f"Connection test failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    loop.close()
