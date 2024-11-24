"""
Main application entry point
"""
from flask import Flask
from flask_cors import CORS
from api.config.config import Config
from api.controllers import register_blueprints


def create_app():
    """Create and configure the Flask application"""
    app = Flask(__name__)
    CORS(app)  # Enable CORS

    # Load configuration
    app.config.from_object(Config)

    # Register all blueprints
    register_blueprints(app)

    return app


def main():
    """Main entry point"""
    app = create_app()
    app.run(
        debug=app.config['DEBUG'],
        host=app.config['HOST'],
        port=app.config['PORT'],
        processes=1,
        threaded=False
    )


if __name__ == '__main__':
    main()
