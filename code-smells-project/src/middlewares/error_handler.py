"""Tratamento de erro centralizado.

Um lugar converte excecao em resposta. Antes eram dezessete blocos
`except Exception as e: return jsonify({"erro": str(e)}), 500` iguais, que
devolviam ao cliente o texto do erro do driver — incluindo nomes de tabelas e
colunas — e tornavam impossivel distinguir 400 de 500 sem editar dezessete
lugares.
"""
import logging

from flask import jsonify
from werkzeug.exceptions import HTTPException

from src.errors import AppError

logger = logging.getLogger(__name__)

MENSAGEM_GENERICA = "Erro interno"

# Mensagens curtas para os erros do proprio transporte, no lugar do texto
# verboso padrao do Werkzeug.
MENSAGENS_HTTP = {
    400: "Requisição inválida",
    401: "Autenticação necessária",
    403: "Acesso negado",
    404: "Rota não encontrada",
    405: "Método não permitido",
    413: "Corpo da requisição muito grande",
    415: "Content-Type não suportado",
    429: "Muitas requisições. Tente novamente em instantes.",
}


def _corpo(mensagem, detalhes=None):
    corpo = {"erro": mensagem, "sucesso": False}
    if detalhes:
        corpo["detalhes"] = detalhes
    return corpo


def register_error_handlers(app):
    @app.errorhandler(AppError)
    def _erro_de_aplicacao(erro):
        logger.info(
            "erro tratado",
            extra={"tipo": type(erro).__name__, "status": erro.status},
        )
        return jsonify(_corpo(erro.mensagem, erro.detalhes)), erro.status

    @app.errorhandler(HTTPException)
    def _erro_http(erro):
        # Rota inexistente, metodo nao permitido, corpo acima do limite: resposta
        # em JSON, como o resto da API, em vez da pagina HTML padrao.
        mensagem = MENSAGENS_HTTP.get(erro.code, erro.name)
        return jsonify(_corpo(mensagem)), erro.code

    @app.errorhandler(Exception)
    def _erro_inesperado(erro):
        # Detalhe completo no servidor; para o cliente, mensagem generica.
        logger.exception("erro nao tratado")
        return jsonify(_corpo(MENSAGEM_GENERICA)), 500
