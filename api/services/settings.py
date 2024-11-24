"""
Settings service for managing device and user preferences
"""
from api.models.settings import DeviceSettings, UserSettings
from api.services.database import DatabaseService
from api.services.device import device_service
from api.utils.logger import get_logger

logger = get_logger()

class SettingsService:
    """Service for managing settings and preferences"""

    def __init__(self):
        """Initialize settings service"""
        self.db = DatabaseService()

    async def get_preferences(self) -> DeviceSettings:
        """Get current device preferences"""
        try:
            query = """
                SELECT * FROM device_settings
                WHERE user_id = (SELECT id FROM users LIMIT 1)
            """
            result = self.db.execute_query(query)

            if not result:
                # Return default settings
                return DeviceSettings()

            return DeviceSettings(**result[0])
        except Exception as e:
            logger.error(f"Failed to get preferences: {e}", exc_info=True)
            raise

    async def update_preferences(self, settings: DeviceSettings) -> DeviceSettings:
        """Update device preferences"""
        try:
            logger.debug(f"Updating preferences: {settings.to_dict()}")

            if not settings.is_valid():
                raise ValueError(
                    "Invalid settings values. Please check:\n"
                    "- max_speed must be between 1.0-6.0 km/h\n"
                    "- start_speed must be between 1.0-3.0 km/h\n"
                    "- start_speed cannot be greater than max_speed\n"
                    "- sensitivity must be between 1-3"
                )

            # Update device first
            try:
                device_result = await device_service.update_preferences(
                    max_speed=settings.max_speed,
                    start_speed=settings.start_speed,
                    sensitivity=settings.sensitivity,
                    child_lock=settings.child_lock,
                    units_miles=settings.units_miles
                )

                if not device_result.get('success'):
                    raise Exception("Device update failed")

            except Exception as e:
                logger.warning(f"Device update had issues: {e}")
                # Continue with database update even if device update had issues

            # Update database (store in km/h)
            query = """
                INSERT INTO device_settings 
                    (user_id, max_speed, start_speed, sensitivity, 
                     child_lock, units_miles, created_at, updated_at)
                VALUES (
                    (SELECT id FROM users LIMIT 1), 
                    %s, %s, %s, %s, %s, 
                    NOW(), NOW()
                )
                ON CONFLICT (user_id) 
                DO UPDATE SET 
                    max_speed = EXCLUDED.max_speed,
                    start_speed = EXCLUDED.start_speed,
                    sensitivity = EXCLUDED.sensitivity,
                    child_lock = EXCLUDED.child_lock,
                    units_miles = EXCLUDED.units_miles,
                    updated_at = NOW()
                RETURNING *
            """

            params = (
                float(settings.max_speed),
                float(settings.start_speed),
                int(settings.sensitivity),
                bool(settings.child_lock),
                bool(settings.units_miles)
            )

            logger.debug(f"Executing update query with params: {params}")
            result = self.db.execute_query(query, params)

            if not result:
                raise Exception("Failed to update preferences in database")

            # Use the new from_db_row method to create settings
            updated_settings = DeviceSettings.from_db_row(result[0])
            return updated_settings

        except Exception as e:
            logger.error(f"Failed to update preferences: {e}", exc_info=True)
            raise

    async def get_user_settings(self) -> UserSettings:
        """Get user settings"""
        try:
            query = """
                SELECT * FROM users 
                WHERE id = (SELECT id FROM users LIMIT 1)
            """
            result = self.db.execute_query(query)

            if not result:
                raise ValueError("No user found")

            return UserSettings(**result[0])
        except Exception as e:
            logger.error(f"Failed to get user settings: {e}", exc_info=True)
            raise

    async def update_user_settings(self, data: dict) -> UserSettings:
        """Update user settings"""
        try:
            valid_fields = [
                'first_name', 'last_name', 'email',
                'height_cm', 'weight_kg', 'profile_picture_url'
            ]

            # Filter valid fields
            updates = {k: v for k, v in data.items() if k in valid_fields}

            if not updates:
                raise ValueError("No valid fields to update")

            # Build update query
            set_clause = ', '.join(f"{k} = %s" for k in updates)
            query = f"""
                UPDATE users 
                SET {set_clause}, updated_at = NOW()
                WHERE id = (SELECT id FROM users LIMIT 1)
                RETURNING *
            """

            result = self.db.execute_query(query, tuple(updates.values()))
            if not result:
                raise ValueError("Failed to update user settings")

            return UserSettings(**result[0])
        except Exception as e:
            logger.error(f"Failed to update user settings: {e}", exc_info=True)
            raise


# Create singleton instance
settings_service = SettingsService()