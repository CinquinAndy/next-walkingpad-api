"""
Controller for device initialization endpoints
"""
from flask import Blueprint, jsonify
from api.services.initialization import initialization_service
from api.utils.logger import get_logger

logger = get_logger()
bp = Blueprint('initialization', __name__)

@bp.route('/connect', methods=['POST'])
async def prepare_device():
    """
    Prepare device for use by ensuring clean state
    """
    try:
        success, response = await initialization_service.prepare_device()

        if not success:
            return jsonify(response), 400

        return jsonify(response)

    except Exception as e:
        logger.error(f"Device preparation failed: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500