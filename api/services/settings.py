"""
Settings service for managing device and user preferences
"""
from typing import Optional
from api.services.database import DatabaseService
from api.services.device import device_service
from api.models.settings import DeviceSettings, UserSettings


class SettingsService:
    """Service for managing settings and preferences"""

    def __init__(self):
        """Initialize settings service"""
        self.db = DatabaseService()

    async def get_preferences(self) -> DeviceSettings:
        """Get current device preferences"""
        query = """
            SELECT * FROM device_settings
            WHERE user_id = (SELECT id FROM users LIMIT 1)
        """
        result = self.db.execute_query(query)

        if not result:
            # Return default settings
            return DeviceSettings()

        return DeviceSettings(**result[0])

    async def update_preferences(self, settings: DeviceSettings) -> DeviceSettings:
        """Update device preferences"""
        # Update device first
        await device_service.update_preferences(
            max_speed=settings.max_speed,
            start_speed=settings.start_speed,
            sensitivity=settings.sensitivity,
            child_lock=settings.child_lock,
            units_miles=settings.units_miles
        )

        # Then update database
        query = """
            INSERT INTO device_settings 
                (user_id, max_speed, start_speed, sensitivity, 
                 child_lock, units_miles)
            VALUES ((SELECT id FROM users LIMIT 1), %s, %s, %s, %s, %s)
            ON CONFLICT (user_id) 
            DO UPDATE SET 
                max_speed = EXCLUDED.max_speed,
                start_speed = EXCLUDED.start_speed,
                sensitivity = EXCLUDED.sensitivity,
                child_lock = EXCLUDED.child_lock,
                units_miles = EXCLUDED.units_miles
            RETURNING *
        """
        params = (
            settings.max_speed,
            settings.start_speed,
            settings.sensitivity,
            settings.child_lock,
            settings.units_miles
        )

        result = self.db.execute_query(query, params)
        return DeviceSettings(**result[0])

    async def get_user_settings(self) -> UserSettings:
        """Get user settings"""
        query = """
            SELECT * FROM users 
            WHERE id = (SELECT id FROM users LIMIT 1)
        """
        result = self.db.execute_query(query)

        if not result:
            raise ValueError("No user found")

        return UserSettings(**result[0])

    async def update_user_settings(self, data: dict) -> UserSettings:
        """Update user settings"""
        valid_fields = [
            'first_name', 'last_name', 'age',
            'height', 'weight', 'profile_picture_url'
        ]

        # Filter valid fields
        updates = {k: v for k, v in data.items() if k in valid_fields}

        if not updates:
            raise ValueError("No valid fields to update")

        # Build update query
        set_clause = ', '.join(f"{k} = %s" for k in updates)
        query = f"""
            UPDATE users 
            SET {set_clause}
            WHERE id = (SELECT id FROM users LIMIT 1)
            RETURNING *
        """

        result = self.db.execute_query(query, tuple(updates.values()))
        return UserSettings(**result[0])


# Create singleton instance
settings_service = SettingsService()