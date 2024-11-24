"""
Settings controller handling device preferences and user settings
"""
from flask import Blueprint, request, jsonify
from api.services.settings import settings_service
from api.models.settings import DeviceSettings

bp = Blueprint('settings', __name__)

@bp.route('/preferences', methods=['GET', 'POST'])
async def handle_preferences():
    """Get or update device preferences"""
    try:
        if request.method == 'GET':
            preferences = await settings_service.get_preferences()
            return jsonify(preferences.to_dict())

        # Parse and validate settings
        settings = DeviceSettings(
            max_speed=int(request.args.get('max_speed', 60)),
            start_speed=int(request.args.get('start_speed', 20)),
            sensitivity=int(request.args.get('sensitivity', 2)),
            child_lock=request.args.get('child_lock', '').lower() == 'true',
            units_miles=request.args.get('units_miles', '').lower() == 'true'
        )

        if not settings.is_valid():
            return jsonify({'error': 'Invalid settings values'}), 400

        # Update preferences
        updated = await settings_service.update_preferences(settings)
        return jsonify(updated.to_dict())

    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

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
