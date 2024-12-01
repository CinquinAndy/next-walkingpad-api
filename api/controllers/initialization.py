"""
Updated device controller with initialization endpoint
"""
from flask import Blueprint, request, jsonify
from api.services.device import device_service
from api.models.device import DeviceMode, SpeedUpdate
from api.services.initialization import initialization_service  # Import the new service
from api.utils.logger import get_logger

logger = get_logger()
bp = Blueprint('initialization', __name__)


@bp.route('/connect', methods=['POST'])
async def initialize_connection():
    """
    Initialize device connection and setup
    This endpoint should be called when the application starts
    """
    try:
        scan_timeout = request.args.get('timeout', default=10, type=int)

        # Run complete initialization sequence
        success, response = await initialization_service.initialize_device()

        if not success:
            return jsonify(response), 400

        return jsonify(response)

    except Exception as e:
        logger.error(f"Initialization failed: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

