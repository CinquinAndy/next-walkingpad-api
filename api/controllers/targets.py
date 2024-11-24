"""
Targets controller handling exercise targets and goals
"""
from flask import Blueprint, request, jsonify
from api.services.targets import targets_service
from api.models.target import Target, TargetType

bp = Blueprint('targets', __name__)


@bp.route('/', methods=['GET'])
async def get_targets():
    """Get current targets"""
    try:
        active_only = request.args.get('active', '').lower() == 'true'
        targets = await targets_service.get_targets(active_only)
        return jsonify([target.to_dict() for target in targets])
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/', methods=['POST'])
async def create_target():
    """Create a new target"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        target_type = data.get('type')
        if not target_type in TargetType.values():
            return jsonify({'error': 'Invalid target type'}), 400

        target = Target(
            type=target_type,
            value=float(data['value']),
            start_date=data.get('start_date'),
            end_date=data.get('end_date')
        )

        created = await targets_service.create_target(target)
        return jsonify(created.to_dict()), 201

    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


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
    """Get progress for all active targets"""
    try:
        target_id = request.args.get('target_id')
        if target_id:
            progress = await targets_service.get_target_progress(int(target_id))
            return jsonify(progress.to_dict())

        progress = await targets_service.get_all_targets_progress()
        return jsonify([p.to_dict() for p in progress])

    except Exception as e:
        return jsonify({'error': str(e)}), 500


