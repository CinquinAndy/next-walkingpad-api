"""
Targets controller
"""
from flask import Blueprint, request, jsonify

from api.models.target import TargetType, Target
from api.services.targets import TargetsService
from api.utils.logger import get_logger

logger = get_logger()
bp = Blueprint('targets', __name__)
targets_service = TargetsService()

@bp.route('/', methods=['GET'])
async def get_targets():
    """Get current targets"""
    try:
        user_id = request.args.get('user_id', type=int)
        active_only = request.args.get('active', 'true').lower() == 'true'

        logger.debug(f"Getting targets for user_id: {user_id}, active_only: {active_only}")
        targets = await targets_service.get_targets(user_id, active_only)

        return jsonify({
            'status': 'success',
            'data': [target.to_dict() for target in targets]
        })
    except Exception as e:
        logger.error(f"Failed to get targets: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500


@bp.route('/', methods=['POST'])
async def create_target():
    """Create a new target"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'status': 'error',
                'error': 'No data provided'
            }), 400

        # Validate required fields
        required_fields = ['type', 'value']
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            return jsonify({
                'status': 'error',
                'error': f"Missing required fields: {', '.join(missing_fields)}"
            }), 400

        # Validate target type
        if not data['type'] in TargetType.values():
            return jsonify({
                'status': 'error',
                'error': f"Invalid target type. Must be one of: {', '.join(TargetType.values())}"
            }), 400

        # Create target
        created = await targets_service.create_target(data)

        return jsonify({
            'status': 'success',
            'message': 'Target created successfully',
            'data': created.to_dict()
        }), 201

    except ValueError as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 400
    except Exception as e:
        logger.error(f"Failed to create target: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500


@bp.route('/<int:target_id>', methods=['PUT'])
async def update_target(target_id: int):
    """Update an existing target"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        updated = await targets_service.update_target(target_id, data)
        return jsonify(updated.to_dict())

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/<int:target_id>', methods=['DELETE'])
async def delete_target(target_id: int):
    """Delete a target"""
    try:
        await targets_service.delete_target(target_id)
        return jsonify({'message': 'Target deleted successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/progress', methods=['GET'])
async def get_target_progress():
    """Get progress for targets"""
    try:
        target_id = request.args.get('target_id')

        if target_id:
            # Get progress for specific target
            progress = await targets_service.get_target_progress(int(target_id))
            if not progress:
                return jsonify({
                    'status': 'error',
                    'error': 'Target not found'
                }), 404

            return jsonify({
                'status': 'success',
                'data': progress.to_dict()
            })

        # Get progress for all active targets
        progress_list = await targets_service.get_all_targets_progress()
        return jsonify({
            'status': 'success',
            'data': [p.to_dict() for p in progress_list]
        })

    except ValueError as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 400
    except Exception as e:
        logger.error(f"Failed to get target progress: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500
