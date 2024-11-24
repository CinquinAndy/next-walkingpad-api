"""
WalkingPad API main application entry point
"""
import os
from dotenv import load_dotenv
from flask import Flask
from flask_cors import CORS
from api.config.config import Config
from api.controllers import register_blueprints
from api.utils.logger import get_logger

logger = get_logger()

def create_app():
    """Create and configure the Flask application"""
    # Load environment variables
    load_dotenv()

    # Create Flask app
    app = Flask(__name__)
    CORS(app)

    # Load configuration
    app.config.from_object(Config)

    try:
        # Register blueprints for all controllers
        register_blueprints(app)
        logger.info("Application initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize application: {e}")
        raise

    return app

def main():
    """Main application entry point"""
    app = create_app()

    host = os.getenv('HOST', '0.0.0.0')
    port = int(os.getenv('PORT', 5678))
    debug = os.getenv('DEBUG', 'False').lower() == 'true'

    logger.info(f"Starting server on {host}:{port} (debug={debug})")

    app.run(
        host=host,
        port=port,
        debug=debug,
        use_reloader=debug,
        processes=1,
        threaded=False
    )

if __name__ == '__main__':
    main()