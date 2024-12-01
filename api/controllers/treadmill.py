"""
Simple treadmill control endpoints for basic operations
- Setup/reset state
- Start walking
- Stop walking
"""
from flask import Blueprint, jsonify
import asyncio

from api.services.device import device_service
from api.services.security import ExerciseSecurityService
from api.services.database import DatabaseService
from api.utils.logger import get_logger

logger = get_logger()
bp = Blueprint('treadmill', __name__)

# Initialize security service for state checks
security_service = ExerciseSecurityService(DatabaseService(), device_service)


@bp.route('/setup', methods=['POST'])
async def setup_treadmill():
    """
    Reset and prepare treadmill for use
    - Checks current state
    - Cleans up any incomplete sessions
    - Ensures proper mode
    """
    try:
        # Verify and clean device state
        is_ready, error_message = await security_service.check_and_clean_state()
        if not is_ready:
            logger.warning(f"Setup failed: {error_message}")
            return jsonify({
                'status': 'error',
                'message': error_message
            }), 400

        # Connect and ensure proper mode
        await device_service.connect()
        await device_service.controller.stop_belt()
        await asyncio.sleep(device_service.minimal_cmd_space)
        await device_service.controller.switch_mode(2)  # Set to standby

        return jsonify({
            'status': 'success',
            'message': 'Treadmill ready for use',
            'state': 'standby'
        })

    except Exception as e:
        logger.error(f"Setup failed: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@bp.route('/start', methods=['POST'])
async def start_treadmill():
    """
    Start the treadmill in manual mode
    - Ensures device is ready
    - Sets manual mode
    - Starts belt
    """
    try:
        await device_service.connect()

        # Set manual mode and start
        await device_service.controller.switch_mode(1)  # Manual mode
        await asyncio.sleep(device_service.minimal_cmd_space)
        await device_service.controller.start_belt()

        # Verify start was successful
        status = await device_service.get_status()

        return jsonify({
            'status': 'success',
            'message': 'Treadmill started',
            'data': {
                'mode': status.get('mode', 'manual'),
                'belt_state': status.get('belt_state', 'running'),
                'speed': status.get('speed', 0)
            }
        })

    except Exception as e:
        logger.error(f"Start failed: {e}")
        # Try to stop in case of error
        try:
            await device_service.controller.stop_belt()
        except:
            pass
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@bp.route('/stop', methods=['POST'])
async def stop_treadmill():
    """
    Stop the treadmill
    - Stops belt movement
    - Sets standby mode
    """
    try:
        await device_service.connect()

        # Stop belt first
        await device_service.controller.stop_belt()
        await asyncio.sleep(device_service.minimal_cmd_space)

        # Set standby mode
        await device_service.controller.switch_mode(2)

        return jsonify({
            'status': 'success',
            'message': 'Treadmill stopped',
            'state': 'standby'
        })

    except Exception as e:
        logger.error(f"Stop failed: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500