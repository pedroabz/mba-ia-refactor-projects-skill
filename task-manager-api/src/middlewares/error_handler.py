"""Centralized error handling (T-14).

Replaces twelve bare `except:` clauses and ten hand-written generic messages.
Controllers raise; this module is the only place that turns an error into a
response, so the error envelope cannot drift between handlers.

The envelope keeps the original `{"error": "<message>"}` shape and adds an
optional `details` object for field-level validation output, so a client
reading `.error` is unaffected.
"""
from flask import jsonify
from werkzeug.exceptions import HTTPException

from src.config.logging_config import get_logger

logger = get_logger(__name__)


class AppError(Exception):
    """Base class for errors with a known client-facing meaning."""

    status = 500
    message = "Erro interno"

    def __init__(self, message: str | None = None, details=None):
        super().__init__(message or self.message)
        if message:
            self.message = message
        self.details = details


class BadRequest(AppError):
    status, message = 400, "Dados inválidos"


class ValidationFailed(AppError):
    status, message = 400, "Dados inválidos"


class Unauthorized(AppError):
    status, message = 401, "Não autenticado"


class Forbidden(AppError):
    status, message = 403, "Acesso negado"


class NotFound(AppError):
    status, message = 404, "Recurso não encontrado"


class Conflict(AppError):
    status, message = 409, "Conflito"


def register_error_handlers(app) -> None:
    @app.errorhandler(AppError)
    def _handle_app_error(error: AppError):
        body = {"error": error.message}
        if error.details:
            body["details"] = error.details
        if error.status >= 500:
            logger.error("application error: %s", error.message)
        else:
            logger.info("client error %d: %s", error.status, error.message)
        return jsonify(body), error.status

    @app.errorhandler(HTTPException)
    def _handle_http_exception(error: HTTPException):
        """Framework-raised errors answer in JSON too.

        Without this, an unmatched route or an oversized body returns Werkzeug's
        HTML page from an API that otherwise speaks only JSON.
        """
        logger.info("http error %s on %s", error.code, error.name)
        return jsonify({"error": error.description}), error.code or 500

    @app.errorhandler(Exception)
    def _handle_unexpected(error: Exception):
        # Full detail server-side, nothing leaked to the client. The old code
        # printed the exception and discarded the traceback.
        logger.exception("unhandled error: %s", type(error).__name__)
        return jsonify({"error": "Erro interno"}), 500
