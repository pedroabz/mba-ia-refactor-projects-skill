"""Fluxo HTTP dos casos de uso de pedido.

As regras do checkout e da transicao de status ficam no `PedidoService`; aqui
estao apenas a leitura da requisicao, a verificacao de quem pode ver o que, e a
forma da resposta.
"""
import logging

from flask import jsonify, request

from src.errors import Forbidden
from src.middlewares.auth import usuario_atual
from src.views import schemas, serializers

logger = logging.getLogger(__name__)

TIPO_ADMIN = "admin"


class PedidoController:
    def __init__(self, pedido_model, pedido_service, settings):
        self._pedidos = pedido_model
        self._service = pedido_service
        self._settings = settings

    def _paginacao(self):
        return schemas.parse_paginacao(
            request.args,
            self._settings.DEFAULT_PAGE_SIZE,
            self._settings.MAX_PAGE_SIZE,
        )

    def criar(self):
        dados = schemas.validar_pedido(request.get_json(silent=True))

        chamador = usuario_atual()
        if chamador["tipo"] != TIPO_ADMIN and chamador["id"] != dados["usuario_id"]:
            raise Forbidden("Não é possível criar pedido para outro usuário")

        resultado = self._service.criar(dados["usuario_id"], dados["itens"])
        return jsonify(serializers.ok(resultado, "Pedido criado com sucesso")), 201

    def listar_todos(self):
        limit, offset = self._paginacao()
        rows = self._pedidos.listar_com_itens(limit, offset)
        return jsonify(serializers.pagina(
            serializers.agrupar_pedidos(rows),
            total=self._pedidos.contar(),
            limit=limit,
            offset=offset,
        )), 200

    def listar_do_usuario(self, usuario_id):
        chamador = usuario_atual()
        if chamador["tipo"] != TIPO_ADMIN and chamador["id"] != usuario_id:
            raise Forbidden("Não é possível ver pedidos de outro usuário")

        limit, offset = self._paginacao()
        rows = self._pedidos.listar_do_usuario_com_itens(usuario_id, limit, offset)
        return jsonify(serializers.pagina(
            serializers.agrupar_pedidos(rows),
            total=self._pedidos.contar_do_usuario(usuario_id),
            limit=limit,
            offset=offset,
        )), 200

    def atualizar_status(self, pedido_id):
        novo_status = schemas.validar_status_pedido(request.get_json(silent=True))
        self._service.atualizar_status(pedido_id, novo_status)
        return jsonify(serializers.ok(mensagem="Status atualizado")), 200
