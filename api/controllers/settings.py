"""
Settings controller handling device preferences and user settings
"""
from flask import Blueprint, request, jsonify
from api.services.settings import settings_service
from api.models.settings import DeviceSettings
from api.utils.logger import logger

bp = Blueprint('settings', __name__)

@bp.route('/preferences', methods=['GET', 'POST'])
async def handle_preferences():
    """Get or update device preferences"""
    try:
        if request.method == 'GET':
            preferences = await settings_service.get_preferences()
            return jsonify({
                'status': 'success',
                'data': preferences.to_dict()
            })

        # For POST, get data from query parameters and convert to appropriate units
        # Speed values are received in km/h and need to be converted for the device
        settings = DeviceSettings(
            # Convert speeds from km/h to device units (e.g., 6.0 -> 60)
            max_speed=float(request.args.get('max_speed', '6.0')),
            start_speed=float(request.args.get('start_speed', '2.0')),
            # Sensitivity: 1=high, 2=medium, 3=low
            sensitivity=int(request.args.get('sensitivity', '2')),
            child_lock=request.args.get('child_lock', '').lower() == 'true',
            units_miles=request.args.get('units_miles', '').lower() == 'true'
        )

        # Validate settings
        if not settings.is_valid():
            return jsonify({
                'status': 'error',
                'error': 'Invalid settings values',
                'details': {
                    'max_speed': 'Must be between 1.0-6.0 km/h',
                    'start_speed': 'Must be between 1.0-3.0 km/h',
                    'sensitivity': 'Must be between 1-3',
                }
            }), 400

        # Update preferences
        updated = await settings_service.update_preferences(settings)
        return jsonify({
            'status': 'success',
            'message': 'Preferences updated successfully',
            'data': updated.to_dict()
        })

    except ValueError as e:
        logger.error(f"Invalid settings values: {e}")
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 400
    except Exception as e:
        logger.error(f"Failed to handle preferences: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

@bp.route('/user', methods=['GET', 'PUT'])
async def handle_user_settings():
    """Get or update user settings"""
    try:
        if request.method == 'GET':
            settings = await settings_service.get_user_settings()
            return jsonify(settings.to_dict())

        # Update user settings
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        updated = await settings_service.update_user_settings(data)
        return jsonify(updated.to_dict())

    except Exception as e:
        return jsonify({'error': str(e)}), 500
