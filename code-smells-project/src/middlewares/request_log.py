"""Log de requisicoes, registrado uma vez em vez de copiado por handler."""
import logging

from flask import request

logger = logging.getLogger(__name__)


def register_request_logging(app):
    @app.after_request
    def _registrar(response):
        logger.info(
            "requisicao atendida",
            extra={
                "metodo": request.method,
                "rota": request.path,
                "status": response.status_code,
            },
        )
        return response
