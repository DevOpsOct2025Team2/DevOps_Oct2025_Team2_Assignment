import os
from app import create_app
import logging

logger = logging.getLogger(__name__)

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
    logger.info("Starting Flask app on %s:%d (debug=%s)", host, port, debug_mode)
    app.run(host=host, port=port, debug=debug_mode, use_reloader=False)