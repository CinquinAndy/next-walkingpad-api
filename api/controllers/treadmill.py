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
    Stream real-time treadmill data with proper state management
    Stops automatically when belt state is idle or device disconnects
    """

    def generate():
        async def get_metrics():
            idle_count = 0  # Counter for consecutive idle states
            MAX_IDLE_COUNT = 3  # Number of consecutive idle states before stopping

            try:
                # Initial connection
                await device_service.connect()

                while True:
                    try:
                        status = await device_service.get_status()

                        # Prepare metric data
                        data = {
                            'timestamp': datetime.now().isoformat(),
                            'distance_km': float(status.get('distance', 0)),
                            'steps': int(status.get('steps', 0)),
                            'time': int(status.get('time', 0)),
                            'speed': float(status.get('speed', 0)),
                            'belt_state': status.get('belt_state', 'unknown')
                        }

                        # Check for idle state or stopped state
                        if data['belt_state'] in ['idle', 'standby'] and data['speed'] == 0:
                            idle_count += 1
                            if idle_count >= MAX_IDLE_COUNT:
                                logger.info("Treadmill stopped - ending stream")
                                # Send final state before stopping
                                yield f"data: {json.dumps(data)}\n\n"
                                break
                        else:
                            idle_count = 0  # Reset counter if not idle

                        yield f"data: {json.dumps(data)}\n\n"
                        await asyncio.sleep(1.0)  # 1 second update interval

                    except Exception as e:
                        if "Unreachable" in str(e) or "disconnected" in str(e).lower():
                            logger.warning("Device disconnected - ending stream")
                            yield f"data: {json.dumps({'status': 'disconnected', 'error': str(e)})}\n\n"
                            break
                        else:
                            logger.error(f"Error getting metrics: {e}")
                            continue

            except Exception as e:
                logger.error(f"Stream error: {e}")
                yield f"data: {json.dumps({'status': 'error', 'error': str(e)})}\n\n"

            finally:
                try:
                    await device_service.disconnect()
                except Exception as e:
                    logger.error(f"Error disconnecting: {e}")

        # Create and manage event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            it = get_metrics()
            while True:
                try:
                    data = loop.run_until_complete(anext(it))
                    if data:  # Only yield if we have data
                        yield data
                except StopAsyncIteration:
                    break
                except Exception as e:
                    logger.error(f"Iterator error: {e}")
                    break
        finally:
            loop.close()

    return Response(
        generate(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Content-Type': 'text/event-stream',
            'X-Accel-Buffering': 'no'  # Disable proxy buffering
        }
    )