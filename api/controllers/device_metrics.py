"""
Simple device metrics controller for real-time data streaming
"""
from flask import Blueprint, Response
import json
import asyncio
from datetime import datetime

from api.services.device_metrics import deviceMetrics_service
from api.utils.logger import get_logger

logger = get_logger()
bp = Blueprint('device_metrics', __name__)


@bp.route('/metrics/stream', methods=['GET'])
async def stream_raw_metrics():
    """Stream raw metrics directly from the device"""

    def generate():
        async def get_device_data():
            try:
                # Initial connection
                await deviceMetrics_service.connect()
                while True:
                    status = await deviceMetrics_service.get_status()
                    if status:
                        data = {
                            'timestamp': datetime.now().isoformat(),
                            'distance_km': float(status.get('distance', 0)),
                            'steps': int(status.get('steps', 0)),
                            'time': int(status.get('time', 0)),
                            'speed': float(status.get('speed', 0)),
                            'belt_state': status.get('belt_state', 'unknown')
                        }
                        yield f"data: {json.dumps(data)}\n\n"
                    await asyncio.sleep(0.5)  # Polling interval
            except Exception as e:
                logger.error(f"Stream error: {e}")
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
            finally:
                # Cleanup
                try:
                    await deviceMetrics_service.disconnect()
                except Exception as e:
                    logger.error(f"Disconnect error: {e}")

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            it = get_device_data()
            while True:
                try:
                    data = loop.run_until_complete(anext(it))
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
            'Content-Type': 'text/event-stream'
        }
    )