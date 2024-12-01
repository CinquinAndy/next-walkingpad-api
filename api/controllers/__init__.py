"""
Controllers initialization and blueprint registration.
Configures all API routes and their respective URL prefixes.
"""
from flask import Flask
from . import (
    device,           # Device control endpoints
    exercise,         # exercise endpoints
    settings,         # Settings and preferences
    initialization,   # Device initialization
    targets          # Exercise targets and goals
)
from api.utils.logger import logger

def register_blueprints(app: Flask) -> None:
    """
    Register all blueprints with the Flask application.

    Args:
        app: Flask application instance

    Each blueprint is mounted at its respective URL prefix.
    """
    logger.info("Registering API blueprints")

    # Core functionality
    app.register_blueprint(device.bp, url_prefix='/api/device')
    app.register_blueprint(settings.bp, url_prefix='/api/settings')
    app.register_blueprint(targets.bp, url_prefix='/api/targets')
    app.register_blueprint(initialization.bp, url_prefix='/api/initialization')

    # Exercise endpoints (both traditional and streaming)
    app.register_blueprint(exercise.bp, url_prefix='/api/exercise')

    logger.info("Blueprint registration complete")