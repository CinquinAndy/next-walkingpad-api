"""
Controllers initialization and blueprint registration
"""
from . import device, exercise, settings, targets
from api.utils.logger import logger

def register_blueprints(app):
    logger.info("[controllers __init__] - Registering blueprints")
    """Register all blueprints with the application"""
    app.register_blueprint(device.bp, url_prefix='/api/device')
    app.register_blueprint(exercise.bp, url_prefix='/api/exercise')
    app.register_blueprint(settings.bp, url_prefix='/api/settings')
    app.register_blueprint(targets.bp, url_prefix='/api/targets')
