"""
Device controller handling device-related endpoints
"""
from flask import Blueprint, request, jsonify
from api.services.device import device_service
from api.models.device import DeviceMode, SpeedUpdate

bp = Blueprint('device', __name__)


@bp.route('/status', methods=['GET'])
async def get_status():
    """Get current device status"""
    try:
        status = await device_service.get_status()
        return jsonify(status)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/mode', methods=['GET', 'POST'])
async def handle_mode():
    """Get or set device mode"""
    try:
        if request.method == 'GET':
            mode = await device_service.get_mode()
            return jsonify({'mode': mode})

        new_mode = request.args.get('new_mode', '').lower()
        if new_mode not in DeviceMode.valid_modes():
            return jsonify({'error': f'Mode {new_mode} not supported'}), 400

        await device_service.set_mode(new_mode)
        return jsonify({'mode': new_mode})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/speed', methods=['POST'])
async def change_speed():
    """Change walking pad speed"""
    try:
        speed = int(request.args.get('speed', 0))
        update = SpeedUpdate(speed)

        if not update.is_valid():
            return jsonify({'error': 'Speed must be between 0 and 60 (0-6.0 km/h)'}), 400

        await device_service.set_speed(speed)
        return jsonify({'speed': speed / 10})

    except ValueError:
        return jsonify({'error': 'Invalid speed value'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/stop', methods=['POST'])
async def stop_device():
    """Emergency stop"""
    try:
        await device_service.stop()
        return jsonify({'message': 'Walking pad stopped successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/calibrate', methods=['POST'])
async def calibrate_device():
    """Calibrate the walking pad"""
    try:
        await device_service.calibrate()
        return jsonify({'message': 'Calibration initiated'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


