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

@bp.route('/stop', methods=['POST'])
async def stop_treadmill():
    """Stop the treadmill"""
    try:
        # S'assurer d'une connexion propre
        if not device_service.is_connected:
            await device_service.connect()
            await asyncio.sleep(device_service.minimal_cmd_space)

        # Séquence d'arrêt
        await device_service.controller.stop_belt()
        await asyncio.sleep(device_service.minimal_cmd_space)

        # Vérifier l'arrêt
        await device_service.controller.ask_stats()
        await asyncio.sleep(device_service.minimal_cmd_space)

        # Passer en mode standby
        await device_service.controller.switch_mode(2)
        await asyncio.sleep(device_service.minimal_cmd_space)

        # Déconnexion propre
        await device_service.disconnect()

        return jsonify({
            'status': 'success',
            'message': 'Treadmill stopped',
            'state': 'standby'
        })

    except Exception as e:
        logger.error(f"Stop failed: {e}")
        # Tentative de nettoyage en cas d'erreur
        try:
            if device_service.is_connected:
                await device_service.controller.stop_belt()
                await device_service.disconnect()
        except Exception as cleanup_error:
            logger.error(f"Cleanup after error failed: {cleanup_error}")

        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@bp.route('/start', methods=['POST'])
async def start_treadmill():
    """Start the treadmill in manual mode"""
    try:
        # S'assurer que le device est déconnecté avant de commencer
        if device_service.is_connected:
            await device_service.disconnect()
            await asyncio.sleep(1)

        # Nouvelle connexion
        await device_service.connect()
        await asyncio.sleep(device_service.minimal_cmd_space)

        # Set manual mode and start
        await device_service.controller.switch_mode(1)  # Manual mode
        await asyncio.sleep(device_service.minimal_cmd_space)

        await device_service.controller.start_belt()
        await asyncio.sleep(device_service.minimal_cmd_space)

        # Vérifier le statut
        await device_service.controller.ask_stats()
        await asyncio.sleep(device_service.minimal_cmd_space)

        status = device_service.controller.last_status

        return jsonify({
            'status': 'success',
            'message': 'Treadmill started',
            'data': {
                'mode': 'manual',
                'belt_state': 'running',
                'speed': status.speed / 10 if status else 0
            }
        })

    except Exception as e:
        logger.error(f"Start failed: {e}")
        # Cleanup en cas d'erreur
        try:
            await device_service.controller.stop_belt()
            await device_service.disconnect()
        except:
            pass
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@bp.route('/stream', methods=['GET'])
def stream_treadmill_data():
    """Stream real-time treadmill data"""
    logger.info("Stream endpoint called")

    def generate():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        logger.info("Generate function started")

        async def async_generate():
            try:
                # Connexion initiale
                if not device_service.is_connected:
                    await device_service.connect()
                    await asyncio.sleep(1)

                while True:
                    try:
                        # Vérifier la connexion
                        if not device_service.is_connected:
                            await device_service.connect()
                            await asyncio.sleep(1)

                        # Demander les stats
                        await device_service.controller.ask_stats()
                        await asyncio.sleep(0.5)

                        status = device_service.controller.last_status

                        if not status:
                            continue

                        # Convertir le status en dictionnaire
                        status_dict = {
                            'distance': float(status.dist) / 100,
                            'time': int(status.time),
                            'steps': int(status.steps),
                            'speed': float(status.speed) / 10,
                            'state': status.belt_state,  # Changé de status.state à status.belt_state
                            'mode': status.manual_mode,  # Changé de status.mode à status.manual_mode
                            'app_speed': float(status.app_speed) / 30 if status.app_speed > 0 else 0,
                            'button': status.controller_button,
                            'timestamp': datetime.now().isoformat()
                        }

                        yield f"data: {json.dumps(status_dict)}\n\n"
                        await asyncio.sleep(0.5)

                    except Exception as e:
                        logger.error(f"Error during stream: {e}")
                        yield f"data: {json.dumps({'error': str(e)})}\n\n"
                        await asyncio.sleep(1)

            except Exception as e:
                logger.error(f"Fatal error in stream: {e}")
                yield f"data: {json.dumps({'error': 'Stream terminated'})}\n\n"

            finally:
                try:
                    if device_service.is_connected:
                        await device_service.disconnect()
                except Exception as e:
                    logger.error(f"Error during disconnect: {e}")

        # Exécuter le générateur asynchrone
        async_gen = async_generate()
        while True:
            try:
                data = loop.run_until_complete(async_gen.__anext__())
                yield data
            except StopAsyncIteration:
                break
            except Exception as e:
                logger.error(f"Stream error: {e}")
                break

        if not loop.is_closed():
            loop.close()

    return Response(
        generate(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Content-Type': 'text/event-stream'
        }
    )


def async_to_sync(async_generator):
    """Convert async generator to sync generator"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)  # Définir explicitement la boucle

    try:
        while True:
            try:
                yield loop.run_until_complete(async_generator.__anext__())
            except StopAsyncIteration:
                break
    finally:
        loop.close()
