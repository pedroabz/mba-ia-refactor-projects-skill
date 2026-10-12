"""Task entry surface: path -> guard -> controller.

Guards are applied here rather than inside the controllers, so a controller
cannot be reached unguarded. Every task route requires an authenticated
caller; none was protected before (SEC-05).
"""
from flask import Blueprint

from src.controllers import task_controller
from src.middlewares.auth import require_auth
from src.middlewares.rate_limit import destructive_limit

task_bp = Blueprint('tasks', __name__)

task_bp.add_url_rule(
    '/tasks', view_func=require_auth(task_controller.list_tasks), methods=['GET'])
task_bp.add_url_rule(
    '/tasks', view_func=require_auth(task_controller.create_task), methods=['POST'])
task_bp.add_url_rule(
    '/tasks/search', view_func=require_auth(task_controller.search_tasks), methods=['GET'])
task_bp.add_url_rule(
    '/tasks/stats', view_func=require_auth(task_controller.task_stats), methods=['GET'])
task_bp.add_url_rule(
    '/tasks/<int:task_id>', view_func=require_auth(task_controller.get_task), methods=['GET'])
task_bp.add_url_rule(
    '/tasks/<int:task_id>', view_func=require_auth(task_controller.update_task), methods=['PUT'])
task_bp.add_url_rule(
    '/tasks/<int:task_id>', view_func=destructive_limit(require_auth(task_controller.delete_task)), methods=['DELETE'])
