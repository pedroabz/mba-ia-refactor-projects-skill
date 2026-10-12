"""Fluxo HTTP do relatorio de vendas."""
from flask import jsonify

from src.views import serializers


class RelatorioController:
    def __init__(self, relatorio_service):
        self._service = relatorio_service

    def vendas(self):
        return jsonify(serializers.ok(self._service.vendas())), 200
