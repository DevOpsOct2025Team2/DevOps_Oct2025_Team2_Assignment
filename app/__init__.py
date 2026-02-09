import os
from flask import Flask
from flask_cors import CORS


def create_app(config_name=None):

    # Create Flask app 
    app = Flask(
        __name__,
        static_folder=os.path.join(os.path.dirname(__file__), '..', 'static'),
        static_url_path='/static',
        template_folder=os.path.join(os.path.dirname(__file__), '..', 'templates')
    )

    # Load configurations
    config_name = config_name or os.getenv('FLASK_ENV', 'development')
    app.config.from_object(
        f'app.config.{config_name.capitalize()}Config'
    )

    # Initialize extensions
    cors_origins = app.config.get("CORS_ORIGINS")

    if cors_origins:
        origins = [
            origin.strip()
            for origin in cors_origins.split(",")
            if origin.strip()
        ]
        CORS(app, supports_credentials=True, origins=origins)
    else:
        CORS(app, supports_credentials=True)

    # Register blueprints
    from app.routes.frontend import frontend_bp
    from app.routes.api import api_bp
    from app.routes import main_bp

    app.register_blueprint(frontend_bp)               # Frontend routes
    app.register_blueprint(main_bp)                   # Main routes
    app.register_blueprint(api_bp, url_prefix='/api/v1')

    # Register error handlers
    from app.errors import register_error_handlers
    register_error_handlers(app)

    # Health check endpoint
    @app.route('/health')
    def health_check():
        return {
            "status": "healthy",
            "version": app.config.get("VERSION", "1.0.0")
        }

    return app
