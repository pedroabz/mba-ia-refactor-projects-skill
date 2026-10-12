"""Category entry surface: path -> guard -> controller.

Paths are unchanged; they were previously registered on the reports blueprint.
Reading the classification list needs authentication; changing a shared
resource that every task references needs a privileged role.
"""
from flask import Blueprint

from src.controllers import category_controller
from src.middlewares.auth import require_auth, require_role
from src.middlewares.rate_limit import destructive_limit
from src.models.user_model import ROLE_ADMIN, ROLE_MANAGER

category_bp = Blueprint('categories', __name__)

_privileged = require_role(ROLE_ADMIN, ROLE_MANAGER)

category_bp.add_url_rule(
    '/categories',
    view_func=require_auth(category_controller.list_categories), methods=['GET'])
category_bp.add_url_rule(
    '/categories',
    view_func=_privileged(category_controller.create_category), methods=['POST'])
category_bp.add_url_rule(
    '/categories/<int:cat_id>',
    view_func=_privileged(category_controller.update_category), methods=['PUT'])
category_bp.add_url_rule(
    '/categories/<int:cat_id>',
    view_func=destructive_limit(_privileged(category_controller.delete_category)), methods=['DELETE'])
