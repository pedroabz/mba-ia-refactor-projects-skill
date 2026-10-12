"""Reporting use cases.

Both handlers are now three lines: resolve, compute, render. The aggregation
they used to perform inline moved to src/services/report_service.py.
"""
from flask import jsonify

from src.middlewares.error_handler import NotFound
from src.models.user_model import User
from src.serializers import report_serializer
from src.services import report_service


def summary_report():
    return jsonify(report_serializer.summary(report_service.summary())), 200


def user_report(user_id):
    user = User.get_by_id(user_id)
    if user is None:
        raise NotFound("Usuário não encontrado")
    return jsonify(report_serializer.user_report(report_service.for_user(user))), 200
