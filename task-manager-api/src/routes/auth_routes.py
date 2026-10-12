"""Authentication entry surface: path -> rate limit -> controller."""
from flask import Blueprint

from src.controllers import auth_controller
from src.middlewares.rate_limit import login_limit

auth_bp = Blueprint('auth', __name__)

auth_bp.add_url_rule(
    '/login', view_func=login_limit(auth_controller.login), methods=['POST'])
