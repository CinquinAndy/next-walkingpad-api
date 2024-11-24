"""
Device related models and types
"""
from dataclasses import dataclass
from typing import Optional

class DeviceMode:
    """Device operation modes"""
    STANDBY = 'standby'
    MANUAL = 'manual'
    AUTO = 'auto'

    @classmethod
    def valid_modes(cls) -> list[str]:
        """Get list of valid modes"""
        return [cls.STANDBY, cls.MANUAL, cls.AUTO]

class BeltState:
    """Belt operation states"""
    STANDBY = 'standby'
    IDLE = 'idle'
    RUNNING = 'running'
    STARTING = 'starting'

@dataclass
class SpeedUpdate:
    """Speed update validation model"""
    speed: int  # Speed in km/h × 10

    def is_valid(self) -> bool:
        """Validate speed value"""
        return 0 <= self.speed <= 60  # 0-6.0 km/h

@dataclass
class DeviceStatus:
    """Current device status model"""
    mode: str
    belt_state: str
    speed: float
    distance: float
    steps: int
    time: int
    calories: Optional[int] = None
    connected: bool = True

    def to_dict(self) -> dict:
        """Convert status to dictionary"""
        return {
            'mode': self.mode,
            'belt_state': self.belt_state,
            'speed': round(self.speed, 1),
            'distance': round(self.distance, 2),
            'steps': self.steps,
            'time': self.time,
            'calories': self.calories,
            'connected': self.connected
        }
