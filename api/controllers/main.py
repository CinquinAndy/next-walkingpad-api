"""
Main controller handling core endpoints and device status
"""
from flask import Blueprint, jsonify
from api.services.device import device_service
from api.utils.logger import get_logger

logger = get_logger()

bp = Blueprint('main', __name__)


@bp.route('/health', methods=['GET'])
async def health_check():
    """API health check endpoint"""
    try:
        device_status = await device_service.get_connection_status()
        return jsonify({
            'status': 'healthy',
            'device_connected': device_status,
            'version': '1.0.0'
        })
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500


@bp.route('/status', methods=['GET'])
async def get_status():
    """Get comprehensive system status"""
    try:
        # Get device status
        device_status = await device_service.get_status()

        return jsonify({
            'device': device_status,
            'api': {
                'status': 'online',
                'version': '1.0.0'
            }
        })
    except Exception as e:
        logger.error(f"Status check failed: {e}")
        return jsonify({
            'error': 'Failed to retrieve status',
            'details': str(e)
        }), 500


