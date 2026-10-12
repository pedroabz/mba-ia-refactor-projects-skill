"""Endpoints de sistema: indice da API, health check e manutencao.

O health check informa disponibilidade e volumes. Nao informa mais configuracao:
a versao anterior devolvia a SECRET_KEY, o caminho do banco, o flag de debug e o
rotulo de ambiente para qualquer chamador anonimo.
"""
import logging

from flask import jsonify

from src.views import serializers

logger = logging.getLogger(__name__)


class SistemaController:
    def __init__(self, manutencao_model, settings):
        self._manutencao = manutencao_model
        self._settings = settings

    def index(self):
        return jsonify({
            "mensagem": "Bem-vindo à API da Loja",
            "versao": self._settings.API_VERSION,
            "endpoints": {
                "produtos": "/produtos",
                "usuarios": "/usuarios",
                "pedidos": "/pedidos",
                "login": "/login",
                "relatorios": "/relatorios/vendas",
                "health": "/health",
            },
        }), 200

    def health(self):
        self._manutencao.ping()
        return jsonify({
            "status": "ok",
            "database": "connected",
            "counts": self._manutencao.contagens(),
            "versao": self._settings.API_VERSION,
        }), 200

    def resetar_banco(self):
        self._manutencao.apagar_tudo()
        logger.warning("banco de dados resetado")
        return jsonify(serializers.ok(mensagem="Banco de dados resetado")), 200
