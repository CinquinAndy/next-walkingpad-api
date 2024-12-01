"""
Controller handling workout sessions and statistics
"""
from flask import Blueprint, jsonify, request
from datetime import datetime, date
import json

from api.services.sessions_service import sessions_service
from api.utils.logger import get_logger

logger = get_logger()
bp = Blueprint('sessions', __name__)

@bp.route('/sessions/start', methods=['POST'])
async def start_session():
    """Start a new workout session"""
    try:
        session = await sessions_service.start_session()
        return jsonify({
            'status': 'success',
            'data': {
                'session_id': session.id,
                'start_time': session.start_time.isoformat()
            }
        })
    except ValueError as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 400
    except Exception as e:
        logger.error(f"Failed to start session: {e}")
        return jsonify({
            'status': 'error',
            'message': 'Internal server error'
        }), 500

@bp.route('/sessions/end', methods=['POST'])
async def end_session():
    """End current workout session"""
    try:
        session = await sessions_service.end_session()
        return jsonify({
            'status': 'success',
            'data': {
                'session_id': session.id,
                'duration_seconds': session.duration_seconds,
                'distance_km': session.distance_km,
                'steps': session.steps,
                'calories': session.calories
            }
        })
    except ValueError as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 400
    except Exception as e:
        logger.error(f"Failed to end session: {e}")
        return jsonify({
            'status': 'error',
            'message': 'Internal server error'
        }), 500

@bp.route('/stats/daily', methods=['GET'])
async def get_daily_stats():
    """Get daily workout statistics"""
    try:
        # Parse date from query parameter if provided
        date_str = request.args.get('date')
        target_date = None
        if date_str:
            try:
                target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                return jsonify({
                    'status': 'error',
                    'message': 'Invalid date format. Use YYYY-MM-DD'
                }), 400

        stats = await sessions_service.get_daily_stats(target_date)
        return jsonify({
            'status': 'success',
            'data': {
                'date': stats.date.isoformat(),
                'total_distance': stats.total_distance,
                'total_steps': stats.total_steps,
                'total_duration': stats.total_duration,
                'total_calories': stats.total_calories,
                'sessions_count': stats.sessions_count,
                'average_speed': stats.average_speed
            }
        })
    except Exception as e:
        logger.error(f"Failed to get daily stats: {e}")
        return jsonify({
            'status': 'error',
            'message': 'Internal server error'
        }), 500