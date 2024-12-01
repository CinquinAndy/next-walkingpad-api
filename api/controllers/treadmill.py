"""
Simple treadmill control endpoints for basic operations
- Setup/reset state
- Start walking
- Stop walking
"""
import time
from datetime import datetime

from flask import Blueprint, jsonify, Response, json, app
import asyncio

from ph4_walkingpad.pad import WalkingPadCurStatus

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


def async_to_sync(async_generator):
    """
    Convert an async generator to a sync generator.

    Args:
        async_generator: The async generator to convert

    Yields:
        The values from the async generator in a synchronous way
    """
    loop = asyncio.new_event_loop()
    try:
        while True:
            try:
                yield loop.run_until_complete(async_generator.__anext__())
            except StopAsyncIteration:
                break
    finally:
        loop.close()


@bp.route('/stream', methods=['GET'])
async def stream_treadmill_data():
    """
    Stream real-time treadmill data as Server-Sent Events (SSE).

    Returns:
        Response: A Flask response object configured for SSE streaming
    """
    logger.info("Stream endpoint called")

    async def generate():
        logger.info("Generate function started")

        IDLE_MAX_COUNT = 3
        idle_count = 0

        try:
            while True:
                try:
                    if not device_service.is_connected:
                        logger.info("Connecting to device...")
                        await device_service.connect()
                        await asyncio.sleep(1)

                    # Get current treadmill status
                    status = await device_service.get_status()
                    logger.debug(f"Raw status received: {status}")

                    if status is None:
                        logger.warning("Received null status")
                        continue

                    # Accéder aux données brutes du contrôleur
                    raw_status = device_service.controller.last_status
                    if raw_status and isinstance(raw_status, WalkingPadCurStatus):
                        status_dict = {
                            'distance': float(raw_status.dist) / 100,  # Conversion en km
                            'time': int(raw_status.time),
                            'steps': int(raw_status.steps),
                            'speed': float(raw_status.speed) / 10,  # Conversion en km/h
                            'state': raw_status.belt_state,
                            'mode': raw_status.manual_mode,
                            'app_speed': float(raw_status.app_speed) / 30 if raw_status.app_speed > 0 else 0,
                            'button': raw_status.controller_button
                        }
                    else:
                        # Utiliser le dictionnaire retourné par get_status si pas de données brutes
                        status_dict = status

                    # Vérifier si le tapis est arrêté
                    is_stopped = status_dict['speed'] == 0 and status_dict['state'] in [0, 1]

                    if is_stopped:
                        idle_count += 1
                        if idle_count >= IDLE_MAX_COUNT:
                            logger.info("Belt stopped - ending stream")
                            yield f"data: {json.dumps({'status': 'stopped', 'metrics': status_dict})}\n\n"
                            break
                    else:
                        idle_count = 0

                    data = {
                        'status': 'active',
                        'metrics': {
                            'timestamp': datetime.now().isoformat(),
                            **status_dict
                        }
                    }

                    logger.debug(f"Sending metrics: {data}")
                    yield f"data: {json.dumps(data)}\n\n"

                    await asyncio.sleep(0.5)

                except Exception as e:
                    logger.error(f"Error in metrics loop: {e}")
                    logger.exception("Detailed error trace:")

                    if any(x in str(e).lower() for x in ["unreachable", "disconnected"]):
                        device_service.is_connected = False
                        continue

                    yield f"data: {json.dumps({'status': 'error', 'error': str(e)})}\n\n"
                    await asyncio.sleep(1.0)

        finally:
            if device_service.is_connected:
                try:
                    await device_service.disconnect()
                except Exception as e:
                    logger.error(f"Error during cleanup: {e}")

    return Response(
        async_to_sync(generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Content-Type': 'text/event-stream',
            'X-Accel-Buffering': 'no'
        }
    )