"""Index and health entry surface: path -> controller."""
from flask import Blueprint

from src.controllers import meta_controller

meta_bp = Blueprint('meta', __name__)

meta_bp.add_url_rule('/', view_func=meta_controller.index, methods=['GET'])
meta_bp.add_url_rule('/health', view_func=meta_controller.health, methods=['GET'])
