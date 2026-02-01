from flask import jsonify
from werkzeug.exceptions import HTTPException

def register_error_handlers(app):
    @app.errorhandler(HTTPException)
    def handle_http_exception(error):
        return (
            jsonify({"error": error.name, "message": error.description}),
            error.code,
        )

    @app.errorhandler(Exception)
    def handle_exception(error):
        app.logger.exception("Unhandled exception: %s", error)
        return (
            jsonify({"error": "Internal Server Error", "message": "Unexpected error."}),
            500,
        )