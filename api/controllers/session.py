"""
Controller handling workout sessions and statistics
"""
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from flask import Blueprint, jsonify, request

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
    """End current workout session and save activity data"""
    try:
        # Get activity data from request body
        data = request.get_json()
        if not data:
            return jsonify({
                'status': 'error',
                'message': 'Activity data is required'
            }), 400

        # Validate required fields
        required_fields = ['distance_km', 'steps', 'duration_seconds', 'average_speed']
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            return jsonify({
                'status': 'error',
                'message': f'Missing required fields: {", ".join(missing_fields)}'
            }), 400

        # Validate data types and ranges
        try:
            activity_data = {
                'distance_km': float(data.get('distance_km', 0)),
                'steps': int(data.get('steps', 0)),
                'duration_seconds': int(data.get('duration_seconds', 0)),
                'calories': int(data.get('calories', 0)),
                'average_speed': float(data.get('average_speed', 0)),
                'max_speed': float(data.get('max_speed', 0)),
                'mode': str(data.get('mode', 'manual')),
                'notes': str(data.get('notes', ''))
            }
        except (ValueError, TypeError) as e:
            return jsonify({
                'status': 'error',
                'message': f'Invalid data format: {str(e)}'
            }), 400

        # Validate value ranges
        if activity_data['distance_km'] < 0 or activity_data['distance_km'] > 100:
            return jsonify({
                'status': 'error',
                'message': 'Distance must be between 0 and 100 km'
            }), 400

        if activity_data['steps'] < 0:
            return jsonify({
                'status': 'error',
                'message': 'Steps cannot be negative'
            }), 400

        if activity_data['duration_seconds'] < 0:
            return jsonify({
                'status': 'error',
                'message': 'Duration cannot be negative'
            }), 400

        # Add current timestamp for end_time
        activity_data['end_time'] = datetime.now(timezone.utc)

        # End session with activity data
        session = await sessions_service.end_session(activity_data)

        return jsonify({
            'status': 'success',
            'data': {
                'session_id': session.id,
                'start_time': session.start_time.isoformat(),
                'end_time': session.end_time.isoformat(),
                'duration_seconds': session.duration_seconds,
                'distance_km': session.distance_km,
                'steps': session.steps,
                'calories': session.calories,
                'average_speed': session.average_speed,
                'max_speed': session.max_speed,
                'mode': session.mode,
                'notes': session.notes
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


def validate_datetime(dt_str: str) -> Optional[datetime]:
    """Validate and parse datetime string"""
    try:
        dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
        return dt.astimezone(timezone.utc)
    except (ValueError, AttributeError):
        return None


def validate_session_data(data: Dict[str, Any]) -> tuple[bool, Optional[str], Optional[Dict]]:
    """
    Validate session data and return validation result

    Returns:
        tuple: (is_valid, error_message, validated_data)
    """
    required_fields = {
        'start_time': str,
        'end_time': str,
        'distance_km': (int, float),
        'steps': int,
        'duration': int
    }

    # Check required fields and types
    for field, expected_type in required_fields.items():
        if field not in data:
            return False, f"Missing required field: {field}", None

        value = data[field]
        if not isinstance(value, expected_type):
            return False, f"Invalid type for {field}. Expected {expected_type}", None

    # Validate and parse timestamps
    start_time = validate_datetime(data['start_time'])
    end_time = validate_datetime(data['end_time'])

    if not start_time or not end_time:
        return False, "Invalid datetime format. Use ISO format (e.g., 2024-01-01T12:00:00Z)", None

    if end_time <= start_time:
        return False, "end_time must be after start_time", None

    # Validate numeric ranges
    validations = [
        (data['distance_km'] >= 0, "distance_km must be non-negative"),
        (data['steps'] >= 0, "steps must be non-negative"),
        (data['duration'] >= 0, "duration must be non-negative"),
        (data.get('average_speed', 0) >= 0, "average_speed must be non-negative"),
        (data.get('max_speed', 0) >= 0, "max_speed must be non-negative")
    ]

    for condition, error_message in validations:
        if not condition:
            return False, error_message, None

    # Create validated data dictionary
    validated_data = {
        'start_time': start_time,
        'end_time': end_time,
        'distance_km': float(data['distance_km']),
        'steps': int(data['steps']),
        'duration_seconds': int(data['duration']*60),
        'calories': int(data.get('calories', 0)),
        'average_speed': float(data.get('average_speed', 0)),
        'max_speed': float(data.get('max_speed', 0)),
        'mode': str(data.get('mode', 'manual')),
        'notes': str(data.get('notes', '')),
        'user_id': int(data.get('user_id', 1))  # Default to user 1 if not specified
    }

    return True, None, validated_data


@bp.route('/sessions/manual', methods=['POST'])
async def create_manual_session():
    """Create a manual exercise session"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'status': 'error',
                'message': 'No data provided'
            }), 400

        # Validate input data
        is_valid, error_message, validated_data = validate_session_data(data)
        if not is_valid:
            return jsonify({
                'status': 'error',
                'message': error_message
            }), 400

        # Create session in database
        query = """
            INSERT INTO exercise_sessions (
                user_id, start_time, end_time, duration_seconds,
                distance_km, steps, calories, average_speed,
                max_speed, mode, notes, created_at, updated_at
            ) VALUES (
                %(user_id)s, %(start_time)s, %(end_time)s, %(duration_seconds)s,
                %(distance_km)s, %(steps)s, %(calories)s, %(average_speed)s,
                %(max_speed)s, %(mode)s, %(notes)s, NOW(), NOW()
            )
            RETURNING *;
        """

        result = sessions_service.db.execute_query(query, validated_data)

        if not result:
            raise Exception("Failed to create session")

        session_data = result[0]

        return jsonify({
            'status': 'success',
            'message': 'Manual session created successfully',
            'data': {
                'id': session_data['id'],
                'start_time': session_data['start_time'].isoformat(),
                'end_time': session_data['end_time'].isoformat(),
                'duration_seconds': session_data['duration_seconds'],
                'distance_km': float(session_data['distance_km']),
                'steps': session_data['steps'],
                'calories': session_data['calories'],
                'average_speed': float(session_data['average_speed']),
                'max_speed': float(session_data['max_speed']) if session_data['max_speed'] else None,
                'mode': session_data['mode'],
                'notes': session_data['notes']
            }
        })

    except Exception as e:
        logger.error(f"Failed to create manual session: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500