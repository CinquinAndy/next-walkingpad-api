"""
Simple treadmill control endpoints for basic operations
- Setup/reset state
- Start walking
- Stop walking
"""
from datetime import datetime

from flask import Blueprint, jsonify, Response, json
import asyncio

from api.services.device import device_service
from api.services.security import ExerciseSecurityService
from api.services.database import DatabaseService
from api.utils.logger import get_logger

logger = get_logger()
bp = Blueprint('treadmill', __name__)

# Initialize security service for state checks
security_service = ExerciseSecurityService(DatabaseService(), device_service)


@bp.route('/setup', methods=['POST'])
async def setup_treadmill():
    """
    Reset and prepare treadmill for use
    - Checks current state
    - Cleans up any incomplete sessions
    - Ensures proper mode
    """
    try:
        # Verify and clean device state
        is_ready, error_message = await security_service.check_and_clean_state()
        if not is_ready:
            logger.warning(f"Setup failed: {error_message}")
            return jsonify({
                'status': 'error',
                'message': error_message
            }), 400

        # Connect and ensure proper mode
        await device_service.connect()
        await device_service.controller.stop_belt()
        await asyncio.sleep(device_service.minimal_cmd_space)
        await device_service.controller.switch_mode(2)  # Set to standby

        return jsonify({
            'status': 'success',
            'message': 'Treadmill ready for use',
            'state': 'standby'
        })

    except Exception as e:
        logger.error(f"Setup failed: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@bp.route('/start', methods=['POST'])
async def start_treadmill():
    """
    Start the treadmill in manual mode
    - Ensures device is ready
    - Sets manual mode
    - Starts belt
    """
    try:
        await device_service.connect()

        # Set manual mode and start
        await device_service.controller.switch_mode(1)  # Manual mode
        await asyncio.sleep(device_service.minimal_cmd_space)
        await device_service.controller.start_belt()

        # Verify start was successful
        status = await device_service.get_status()

        return jsonify({
            'status': 'success',
            'message': 'Treadmill started',
            'data': {
                'mode': status.get('mode', 'manual'),
                'belt_state': status.get('belt_state', 'running'),
                'speed': status.get('speed', 0)
            }
        })

    except Exception as e:
        logger.error(f"Start failed: {e}")
        # Try to stop in case of error
        try:
            await device_service.controller.stop_belt()
        except:
            pass
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@bp.route('/stop', methods=['POST'])
async def stop_treadmill():
    """
    Stop the treadmill
    - Stops belt movement
    - Sets standby mode
    """
    try:
        await device_service.connect()

        # Stop belt first
        await device_service.controller.stop_belt()
        await asyncio.sleep(device_service.minimal_cmd_space)

        # Set standby mode
        await device_service.controller.switch_mode(2)

        return jsonify({
            'status': 'success',
            'message': 'Treadmill stopped',
            'state': 'standby'
        })

    except Exception as e:
        logger.error(f"Stop failed: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@bp.route('/stream', methods=['GET'])
async def stream_treadmill_data():
    """
    Stream real-time treadmill data with proper state management and reconnection handling
    """

    def generate():
        async def get_metrics():
            idle_count = 0
            MAX_IDLE_COUNT = 3
            reconnect_attempts = 0
            MAX_RECONNECT_ATTEMPTS = 3
            RECONNECT_DELAY = 2.0

            try:
                while True:
                    try:
                        if not device_service.is_connected:
                            if reconnect_attempts >= MAX_RECONNECT_ATTEMPTS:
                                logger.error("Max reconnection attempts reached")
                                yield f"data: {json.dumps({'status': 'error', 'error': 'Device connection lost'})}\n\n"
                                break

                            logger.info(f"Attempting to reconnect (attempt {reconnect_attempts + 1})")
                            try:
                                await device_service.connect()
                                reconnect_attempts = 0  # Reset counter on successful connection
                            except Exception as conn_err:
                                logger.error(f"Reconnection attempt failed: {conn_err}")
                                reconnect_attempts += 1
                                await asyncio.sleep(RECONNECT_DELAY)
                                continue

                        # Get device status
                        status = await device_service.get_status()

                        # Validate status data
                        if not status or all(v == 0 for v in [status.get('distance', 0),
                                                              status.get('steps', 0),
                                                              status.get('time', 0)]):
                            logger.warning("Received empty or invalid status")
                            idle_count += 1
                            if idle_count >= MAX_IDLE_COUNT:
                                logger.info("Maximum idle readings reached - ending stream")
                                break
                            continue

                        # Reset idle counter if we got valid data
                        idle_count = 0

                        # Prepare metric data
                        data = {
                            'timestamp': datetime.now().isoformat(),
                            'distance_km': float(status.get('distance', 0)),
                            'steps': int(status.get('steps', 0)),
                            'time': int(status.get('time', 0)),
                            'speed': float(status.get('speed', 0)),
                            'belt_state': status.get('belt_state', 'unknown'),
                            'status': 'active'
                        }

                        yield f"data: {json.dumps(data)}\n\n"
                        await asyncio.sleep(1.0)  # 1 second update interval

                    except Exception as e:
                        logger.error(f"Error in metrics loop: {e}")
                        if "Unreachable" in str(e) or "disconnected" in str(e).lower():
                            device_service.is_connected = False
                            continue
                        yield f"data: {json.dumps({'status': 'error', 'error': str(e)})}\n\n"
                        await asyncio.sleep(1.0)

            finally:
                # Ensure proper cleanup
                if device_service.is_connected:
                    try:
                        await device_service.disconnect()
                    except Exception as e:
                        logger.error(f"Error during cleanup: {e}")

        # Create event loop for the generator
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            it = get_metrics()
            while True:
                try:
                    data = loop.run_until_complete(anext(it))
                    if data:
                        yield data
                except StopAsyncIteration:
                    break
                except Exception as e:
                    logger.error(f"Stream iteration error: {e}")
                    break
        finally:
            try:
                loop.close()
            except Exception as e:
                logger.error(f"Error closing loop: {e}")

    return Response(
        generate(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Content-Type': 'text/event-stream',
            'X-Accel-Buffering': 'no'
        }
    )
