"""
Enhanced exercise controller with persistent device connection and efficient metrics streaming
"""
from flask import Blueprint, request, jsonify, Response, current_app
import json
import asyncio
from datetime import datetime, timezone

from api.services.exercise import exercise_service
from api.utils.logger import get_logger

logger = get_logger()
bp = Blueprint('exercise', __name__)

@bp.route('/session/start', methods=['POST'])
async def start_session_stream():
    """Start a new exercise session with persistent device connection"""
    logger.info("Starting new exercise session")
    try:
        # Check if there's already an active session
        if exercise_service.current_session:
            logger.warning("Cannot start new session - another session is active")
            return jsonify({
                'status': 'error',
                'message': 'An active session already exists'
            }), 409

        session = await exercise_service.start_session()
        return jsonify({
            'status': 'success',
            'message': 'Session started successfully',
            'data': {
                'session_id': session.id,
                'start_time': session.start_time.isoformat()
            }
        })

    except Exception as e:
        logger.error(f"Failed to start session: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@bp.route('/session/metrics', methods=['GET'])
async def stream_metrics():
    """
    Stream real-time metrics using a synchronous generator wrapper.
    Handles server-sent events (SSE) properly with Flask.
    """
    if not exercise_service.current_session:
        return jsonify({
            'status': 'error',
            'message': 'No active session'
        }), 404

    def sync_generator():
        """
        Synchronous generator wrapper for async metrics streaming.
        Uses an event loop per request to handle async operations.
        """
        loop = asyncio.new_event_loop()

        async def get_metrics():
            try:
                while exercise_service.current_session:
                    metrics = await exercise_service._get_device_metrics()
                    data = {
                        'status': 'active',
                        'timestamp': datetime.now(timezone.utc).isoformat(),
                        'metrics': {
                            'distance_km': round(metrics['distance_km'], 3),
                            'steps': metrics['steps'],
                            'duration_seconds': metrics['duration_seconds'],
                            'speed': round(metrics['speed'], 2)
                        }
                    }
                    yield f"data: {json.dumps(data)}\n\n"
                    await asyncio.sleep(1.0)
            except Exception as e:
                logger.error(f"Error in metrics stream: {str(e)}")
                yield f"data: {json.dumps({'status': 'error', 'message': str(e)})}\n\n"
            finally:
                loop.stop()

        async def run_metrics():
            async for data in get_metrics():
                yield data

        # Create and run the event loop for this request
        try:
            while True:
                data = loop.run_until_complete(anext(run_metrics()))
                yield data
        except (StopAsyncIteration, RuntimeError):
            return
        except Exception as e:
            logger.error(f"Stream error: {e}")
            return
        finally:
            loop.close()

    return Response(
        sync_generator(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no',
            'Content-Type': 'text/event-stream'
        }
    )


@bp.route('/session/stop', methods=['POST'])
async def stop_session():
    """Stop the current session while maintaining device connection"""
    try:
        if not exercise_service.current_session:
            return jsonify({
                'status': 'error',
                'message': 'No active session found'
            }), 404

        session = await exercise_service.end_session()
        return jsonify({
            'status': 'success',
            'message': 'Session ended successfully',
            'data': session.to_dict()
        })

    except Exception as e:
        logger.error(f"Failed to stop session: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

# Legacy endpoints for backwards compatibility
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