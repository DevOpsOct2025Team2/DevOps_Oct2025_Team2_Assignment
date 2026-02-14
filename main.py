import os
from dotenv import load_dotenv
from app import create_app
import logging

logger = logging.getLogger(__name__)

load_dotenv()

app = create_app()

if __name__ == "__main__":
    debug_mode = os.environ.get("FLASK_DEBUG", "False").lower() == "true"
    host = os.environ.get("FLASK_HOST", "0.0.0.0")
    try:
        port = int(os.environ.get("FLASK_PORT", 5000))
        if not (1 <= port <= 65535):
            raise ValueError("Port must be between 1 and 65535")
    except (ValueError, TypeError):
        logger.warning("Invalid port configuration")
        port = 5000
    
    # Suppress Flask's default verbose output, else it shows all addr
    import logging as werkzeug_logging
    werkzeug_logging.getLogger('werkzeug').setLevel(werkzeug_logging.ERROR)
    
    logger.info("Starting Flask app on http://localhost:%d (debug=%s)", port, debug_mode)
    print(f"\n✓ Flask app running at http://localhost:{port}\n")
    
    app.run(host=host, port=port, debug=debug_mode, use_reloader=False)
