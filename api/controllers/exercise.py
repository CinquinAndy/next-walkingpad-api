"""
Exercise controller handling both real-time sessions and historical data
"""
from flask import Blueprint, request, jsonify, Response
import json
import asyncio

from api.services.exercise import exercise_service  # Keep existing service for stats
from api.services.exercise_stream import exercise_stream_service  # New streaming service
from api.utils.logger import logger

bp = Blueprint('exercise', __name__)

# New streaming endpoints
@bp.route('/session/start', methods=['POST'])
async def start_session_stream():
    """Start a new exercise session with real-time streaming"""
    try:
        session = await exercise_stream_service.start_session()
        return jsonify({
            'status': 'success',
            'message': 'Session started successfully',
            'session_id': session.id
        })
    except Exception as e:
        logger.error(f"Failed to start streaming session: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@bp.route('/session/metrics', methods=['GET'])
async def stream_metrics():
    """Stream current session metrics"""
    async def generate():
        while True:
            metrics = await exercise_stream_service.get_current_metrics()
            if metrics:
                yield f"data: {json.dumps(metrics.__dict__)}\n\n"
            await asyncio.sleep(1.0)

    return Response(
        generate(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Content-Type': 'text/event-stream'
        }
    )

@bp.route('/session/end', methods=['POST'])
async def end_session_stream():
    """End current streaming session"""
    try:
        session = await exercise_stream_service.end_session()
        return jsonify({
            'status': 'success',
            'message': 'Session ended successfully',
            'session': session.to_dict()
        })
    except Exception as e:
        logger.error(f"Failed to end streaming session: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

# Keep existing endpoints for backwards compatibility and stats
@bp.route('/start', methods=['POST'])
async def start_session():
    """Legacy start session endpoint"""
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
    """Legacy end session endpoint"""
    try:
        session = await exercise_service.end_session()
        return jsonify({
            'status': 'success',
            'message': 'Exercise session ended successfully',
            'session': session.to_dict()
        })
    except Exception as e:
        logger.error(f"Error ending session: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@bp.route('/history', methods=['GET'])
async def get_history():
    """Get exercise history"""
    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 10))

        history = await exercise_service.get_history(page, per_page)
        return jsonify(history.to_dict())
    except Exception as e:
        logger.error(f"Failed to get exercise history: {e}")
        return jsonify({'error': str(e)}), 500

@bp.route('/stats', methods=['GET'])
async def get_stats():
    """Get exercise statistics"""
    try:
        period = request.args.get('period', 'daily')
        stats = await exercise_service.get_stats(period)
        return jsonify(stats.to_dict())
    except Exception as e:
        return jsonify({'error': str(e)}), 500