"""Reporting entry surface: path -> guard -> controller.

The summary exposes every user's productivity, so it is privileged. A
per-user report is readable by that user or by a privileged caller.
"""
from flask import Blueprint

from src.controllers import report_controller
from src.middlewares.auth import require_role, require_self_or_privileged
from src.models.user_model import ROLE_ADMIN, ROLE_MANAGER

report_bp = Blueprint('reports', __name__)

report_bp.add_url_rule(
    '/reports/summary',
    view_func=require_role(ROLE_ADMIN, ROLE_MANAGER)(report_controller.summary_report),
    methods=['GET'])
report_bp.add_url_rule(
    '/reports/user/<int:user_id>',
    view_func=require_self_or_privileged()(report_controller.user_report),
    methods=['GET'])
