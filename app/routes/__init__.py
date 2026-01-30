from flask import Blueprint

# web routes
main_bp = Blueprint('main', __name__)

# REST endpoints
api_bp = Blueprint('api', __name__)

from app.routes import main, api