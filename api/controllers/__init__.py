"""
Controllers initialization and blueprint registration.
Configures all API routes and their respective URL prefixes.
"""
from flask import Flask
from . import (
    device,  # Device control endpoints
    settings,  # Settings and preferences
    session, # Exercise session management
    treadmill, # Treadmill control endpoints
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
    app.register_blueprint(treadmill.bp, url_prefix='/api/treadmill')
    app.register_blueprint(device.bp, url_prefix='/api/device')
    app.register_blueprint(settings.bp, url_prefix='/api/settings')
    app.register_blueprint(session.bp, url_prefix='/api/sessions')

    logger.info("Blueprint registration complete")
