"""Authentication use cases."""
from flask import jsonify, request

from src.config.logging_config import get_logger
from src.middlewares.auth import issue_token
from src.middlewares.error_handler import Forbidden, Unauthorized
from src.models.user_model import User
from src.schemas.base import load_or_raise
from src.schemas.user_schema import LOGIN_FIELD_ORDER, LoginSchema
from src.serializers.user_serializer import login_result

logger = get_logger(__name__)


def login():
    data = load_or_raise(
        LoginSchema(), request.get_json(silent=True), field_order=LOGIN_FIELD_ORDER
    )

    user = User.get_by_email(data["email"])
    # One message for both "no such account" and "wrong password", so the
    # endpoint does not confirm which emails are registered.
    if user is None or not user.check_password(data["password"]):
        logger.info("login rejected for %s", data["email"])
        raise Unauthorized("Credenciais inválidas")

    if not user.active:
        raise Forbidden("Usuário inativo")

    # A signed, expiring token. The previous value was the literal string
    # "fake-jwt-token-<id>", which nothing ever verified (SEC-05).
    token = issue_token(user)
    logger.info("login accepted user=%s", user.id)
    return jsonify(login_result(user, token)), 200
