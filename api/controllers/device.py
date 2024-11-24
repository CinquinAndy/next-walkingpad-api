"""
Device controller handling WalkingPad operations
"""
from flask import Blueprint, request, jsonify
from api.services.device import device_service
from api.models.device import DeviceMode, SpeedUpdate
from api.utils.logger import get_logger

logger = get_logger()
bp = Blueprint('device', __name__)

@bp.route('/connect', methods=['POST'])
async def connect_device():
    """Connect to the WalkingPad device"""
    try:
        await device_service.connect()
        return jsonify({'message': 'Connected successfully'})
    except Exception as e:
        logger.error(f"Connection failed: {e}")
        return jsonify({'error': str(e)}), 500

@bp.route('/disconnect', methods=['POST'])
async def disconnect_device():
    """Disconnect from the device"""
    try:
        await device_service.disconnect()
        return jsonify({'message': 'Disconnected successfully'})
    except Exception as e:
        logger.error(f"Disconnect failed: {e}")
        return jsonify({'error': str(e)}), 500

@bp.route('/start', methods=['POST'])
async def start_walking():
    logger.info("[controllers device - start]")
    """Start walking session"""
    try:
        speed = request.args.get('speed', type=int)
        result = await device_service.start_walking(initial_speed=speed)
        return jsonify(result)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Start walking failed: {e}")
        return jsonify({'error': str(e)}), 500

@bp.route('/stop', methods=['POST'])
async def stop_walking():
    """Stop walking session"""
    try:
        result = await device_service.stop_walking()
        return jsonify(result)
    except Exception as e:
        logger.error(f"Stop walking failed: {e}")
        return jsonify({'error': str(e)}), 500

@bp.route('/speed', methods=['POST'])
async def set_speed():
    """Set walking speed"""
    try:
        speed = int(request.args.get('speed', 0))
        speed_update = SpeedUpdate(speed)
        
        if not speed_update.is_valid():
            return jsonify({
                'error': 'Speed must be between 0 and 60 (0-6.0 km/h)'
            }), 400

        result = await device_service.set_speed(speed)
        return jsonify(result)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Speed change failed: {e}")
        return jsonify({'error': str(e)}), 500

@bp.route('/mode', methods=['POST'])
async def set_mode():
    """Set device mode"""
    try:
        new_mode = request.args.get('mode', '').lower()
        if new_mode not in DeviceMode.valid_modes():
            return jsonify({
                'error': f'Invalid mode. Must be one of: {", ".join(DeviceMode.valid_modes())}'
            }), 400

        result = await device_service.set_mode(new_mode)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Mode change failed: {e}")
        return jsonify({'error': str(e)}), 500

@bp.route('/status', methods=['GET'])
async def get_device_status():
    """Get device status"""
    logger.info("[controllers device] - controllers")
    try:
        status = await device_service.get_status()
        return jsonify(status)
    except Exception as e:
        logger.error(f"Status check failed: {e}")
        return jsonify({'error': str(e)}), 500

@bp.route('/calibrate', methods=['POST'])
async def calibrate_device():
    """Calibrate the device"""
    try:
        result = await device_service.calibrate()
        return jsonify(result)
    except Exception as e:
        logger.error(f"Calibration failed: {e}")
        return jsonify({'error': str(e)}), 500
