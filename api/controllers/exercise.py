"""
Exercise controller handling exercise sessions and data
"""
from flask import Blueprint, request, jsonify
from datetime import datetime
from api.services.exercise import exercise_service
from api.models.exercise import ExerciseSession, SessionData
from api.utils.logger import logger

bp = Blueprint('exercise', __name__)


@bp.route('/start', methods=['POST'])
async def start_session():
    """Start a new exercise session"""
    try:
        session = await exercise_service.start_session()
        return jsonify({
            'message': 'Session started successfully',
            'session_id': session.id
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/end', methods=['POST'])
async def end_exercise():
    """End the current exercise session"""
    try:
        session = await exercise_service.end_session()
        return jsonify({
            'status': 'success',
            'message': 'Exercise session ended successfully',
            'session': session.to_dict()
        })
    except ValueError as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 400
    except Exception as e:
        logger.error(f"Unexpected error ending session: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': 'An unexpected error occurred while ending the session'
        }), 500


@bp.route('/current', methods=['GET'])
async def get_current_session():
    """Get current session data"""
    try:
        session = await exercise_service.get_current_session()
        return jsonify(session.to_dict() if session else {})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/history', methods=['GET'])
async def get_history():
    """Get exercise history"""
    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 10))

        history = await exercise_service.get_history(page, per_page)
        return jsonify(history.to_dict())
    except Exception as e:
        logger.error(f"Failed to get exercise history: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@bp.route('/stats', methods=['GET'])
async def get_stats():
    """Get exercise statistics"""
    try:
        period = request.args.get('period', 'daily')  # daily, weekly, monthly
        stats = await exercise_service.get_stats(period)
        return jsonify(stats)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/save', methods=['POST'])
async def save_session():
    """Save exercise session data"""
    try:
        data = request.get_json()
        session_data = SessionData(**data)

        if not session_data.is_valid():
            return jsonify({'error': 'Invalid session data'}), 400

        saved_session = await exercise_service.save_session(session_data)
        return jsonify({
            'message': 'Session saved successfully',
            'data': saved_session.to_dict()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


