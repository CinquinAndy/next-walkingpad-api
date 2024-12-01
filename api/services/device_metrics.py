"""
Simplified deviceMetrics service focusing on raw data access
"""
import asyncio
import logging
from typing import Dict, Optional

from api.utils.logger import get_logger
from ph4_walkingpad.pad import Controller, Scanner

logger = get_logger()


class DeviceMetricsService:
    """Simple deviceMetrics service for direct metrics access"""

    def __init__(self):
        self.controller = None
        self.connected = False
        self.address = None

    async def connect(self) -> None:
        """Connect to deviceMetrics if not already connected"""
        if self.connected:
            return

        try:
            # Scan for deviceMetrics if needed
            if not self.address:
                scanner = Scanner()
                await scanner.scan(timeout=3.0)
                if scanner.walking_belt_candidates:
                    self.address = scanner.walking_belt_candidates[0].address
                else:
                    raise Exception("No WalkingPad deviceMetrics found")

            # Connect to deviceMetrics
            self.controller = Controller(self.address)
            await self.controller.run()
            self.connected = True
            logger.info("Connected to deviceMetrics successfully")

        except Exception as e:
            self.connected = False
            logger.error(f"Connection failed: {e}")
            raise

    async def disconnect(self) -> None:
        """Disconnect from deviceMetrics"""
        if self.controller and self.connected:
            await self.controller.disconnect()
            self.connected = False
            logger.info("Disconnected from deviceMetrics")

    async def get_status(self) -> Dict:
        """Get current deviceMetrics status"""
        if not self.connected:
            await self.connect()

        try:
            await self.controller.ask_stats()
            await asyncio.sleep(0.1)  # Small delay for response

            if not self.controller.last_status:
                return {}

            status = self.controller.last_status
            return {
                'distance': status.dist / 100,  # Convert to km
                'time': status.time,
                'steps': status.steps,
                'speed': status.speed / 10,  # Convert to km/h
                'belt_state': self._get_belt_state(status.belt_state)
            }
        except Exception as e:
            logger.error(f"Failed to get status: {e}")
            raise

    @staticmethod
    def _get_belt_state(state: int) -> str:
        """Convert belt state code to string"""
        states = {
            5: 'standby',
            0: 'idle',
            1: 'running',
            7: 'starting'
        }
        return states.get(state, 'unknown')


# Create singleton instance
deviceMetrics_service = DeviceMetricsService()