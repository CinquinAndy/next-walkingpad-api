# !/usr/bin/env python
"""
Bluetooth device scanner for WalkingPad
Scans for nearby devices and identifies WalkingPad devices
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from api.utils.logger import get_logger
from api.utils.helpers import is_valid_bluetooth_address
from ph4_walkingpad import pad
from ph4_walkingpad.pad import Scanner
from ph4_walkingpad.utils import setup_logging
import yaml

logger = get_logger()


class WalkingPadScanner:
    """WalkingPad device scanner"""

    def __init__(self):
        """Initialize scanner"""
        self.log = setup_logging()
        pad.logger = self.log
        self.scanner = Scanner()
        self.devices = []

    async def scan(self, duration: int = 10):
        """
        Scan for nearby Bluetooth devices

        Args:
            duration: Scan duration in seconds
        """
        logger.info(f"Starting Bluetooth scan (duration: {duration}s)...")
        try:
            self.devices = await self.scanner.scan(timeout=duration)
            await self.process_results()
        except Exception as e:
            logger.error(f"Scan failed: {e}")
            raise

    async def process_results(self):
        """Process and display scan results"""
        walking_pads = []

        logger.info(f"\nFound {len(self.devices)} devices:")
        for device in self.devices:
            device_name = device.name or "Unknown"
            address = device.address

            if not is_valid_bluetooth_address(address):
                logger.warning(f"Invalid address format: {address}")
                continue

            logger.info(f"  {device_name} ({address})")

            # Identify WalkingPad devices
            if "walkingpad" in device_name.lower():
                walking_pads.append({
                    'name': device_name,
                    'address': address
                })

        if walking_pads:
            logger.info("\nFound WalkingPad devices:")
            for pad in walking_pads:
                logger.info(f"  {pad['name']} ({pad['address']})")
                self.update_config(pad['address'])
        else:
            logger.warning("\nNo WalkingPad devices found!")
            logger.info("Make sure your WalkingPad is powered on and in range")

    def update_config(self, address: str):
        """
        Update config.yaml with device address

        Args:
            address: Device MAC address
        """
        try:
            config_path = Path('config.yaml')

            # Create default config if it doesn't exist
            if not config_path.exists():
                config = {'address': '', 'database': {}}
            else:
                with open(config_path, 'r') as f:
                    config = yaml.safe_load(f)

            # Update address if different
            if config.get('address') != address:
                config['address'] = address
                with open(config_path, 'w') as f:
                    yaml.dump(config, f, default_flow_style=False)
                logger.info(f"\nUpdated config.yaml with address: {address}")

        except Exception as e:
            logger.error(f"Failed to update config: {e}")


async def main():
    """Main execution function"""
    scanner = WalkingPadScanner()
    try:
        await scanner.scan()
    except KeyboardInterrupt:
        logger.info("\nScan interrupted by user")
    except Exception as e:
        logger.error(f"Error during scan: {e}")
        sys.exit(1)


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    loop.close()
