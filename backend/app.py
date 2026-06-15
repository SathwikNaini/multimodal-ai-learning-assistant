import logging
import traceback
from flask import Flask, jsonify
from flask_cors import CORS

from backend.config.settings import settings
from backend.routes.health import health_router
from backend.routes.summarize import summarize_router
from backend.utils.exceptions import APIError
from backend.services.gemini_service import verify_gemini_connection

# Verify Gemini API connectivity on startup
verify_gemini_connection()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
)


def create_app():
    app = Flask(__name__)
    
    # Configure limits and CORS from settings
    app.config['MAX_CONTENT_LENGTH'] = settings.MAX_CONTENT_LENGTH
    CORS(app, resources={r'/api/*': {'origins': settings.CORS_ORIGINS}})

    # Register modular blueprints
    app.register_blueprint(health_router)
    app.register_blueprint(summarize_router)

    # Global custom API exception handler
    @app.errorhandler(APIError)
    def handle_api_error(err):
        logging.warning(f"[APIError] {err.status_code}: {err.message}")
        return err.to_response()

    # Generic unhandled exception handler
    @app.errorhandler(Exception)  # Catch all unhandled exceptions
    def handle_generic_error(err):
        tb = traceback.format_exc()
        logging.error(f"[Unhandled Error] {str(err)}\n{tb}")
        
        response_data = {
            'success': False,
            'data': None,
            'error': 'Internal server error'
        }
        
        # Expose diagnostic details in development mode
        if settings.FLASK_DEBUG or settings.FLASK_ENV == 'development' or app.debug:
            response_data['details'] = str(err)
            response_data['traceback'] = tb.split('\n')
            
        status_code = getattr(err, 'code', 500)
        return jsonify(response_data), status_code

    return app


app = create_app()


if __name__ == '__main__':
    # Start Flask server locally with debug configuration
    debug_mode = settings.FLASK_DEBUG or settings.FLASK_ENV == 'development'
    logging.info(f"[Server] Starting server (debug={debug_mode})")
    app.run(debug=debug_mode, port=5000, host='127.0.0.1')
