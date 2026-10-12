"""User entry surface: path -> guard -> controller.

The access model, deny-by-default:
  - POST /users stays public: it is registration.
  - Reading or changing one account requires being that account, or privileged.
  - Listing every account, and deleting one, is privileged only.
"""
from flask import Blueprint

from src.controllers import user_controller
from src.middlewares.auth import require_role, require_self_or_privileged
from src.middlewares.rate_limit import destructive_limit
from src.models.user_model import ROLE_ADMIN, ROLE_MANAGER

user_bp = Blueprint('users', __name__)

# Bulk read of personal data: admin and manager only.
user_bp.add_url_rule(
    '/users',
    view_func=require_role(ROLE_ADMIN, ROLE_MANAGER)(user_controller.list_users),
    methods=['GET'])

# Registration: the one public write in the application.
user_bp.add_url_rule(
    '/users', view_func=user_controller.create_user, methods=['POST'])

user_bp.add_url_rule(
    '/users/<int:user_id>',
    view_func=require_self_or_privileged()(user_controller.get_user),
    methods=['GET'])
user_bp.add_url_rule(
    '/users/<int:user_id>',
    view_func=require_self_or_privileged()(user_controller.update_user),
    methods=['PUT'])
user_bp.add_url_rule(
    '/users/<int:user_id>',
    view_func=destructive_limit(require_role(ROLE_ADMIN)(user_controller.delete_user)),
    methods=['DELETE'])
user_bp.add_url_rule(
    '/users/<int:user_id>/tasks',
    view_func=require_self_or_privileged()(user_controller.get_user_tasks),
    methods=['GET'])
