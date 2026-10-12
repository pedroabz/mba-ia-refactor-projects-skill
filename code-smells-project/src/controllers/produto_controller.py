"""Fluxo HTTP dos casos de uso de produto.

O controller le a requisicao, valida na fronteira, abre a transacao, chama o
model e escolhe o status. Nao contem SQL e nao contem regra que outro chamador
precisaria repetir — as regras de produto vivem no schema de validacao e no model.
"""
import logging

from flask import jsonify, request

from src.errors import NotFound
from src.views import schemas, serializers

logger = logging.getLogger(__name__)


class ProdutoController:
    def __init__(self, db, produto_model, settings):
        self._db = db
        self._produtos = produto_model
        self._settings = settings

    def _paginacao(self):
        return schemas.parse_paginacao(
            request.args,
            self._settings.DEFAULT_PAGE_SIZE,
            self._settings.MAX_PAGE_SIZE,
        )

    def listar(self):
        limit, offset = self._paginacao()
        rows = self._produtos.listar(limit, offset)
        return jsonify(serializers.pagina(
            [serializers.produto(row) for row in rows],
            total=self._produtos.contar(),
            limit=limit,
            offset=offset,
        )), 200

    def buscar(self, produto_id):
        row = self._produtos.buscar_por_id(produto_id)
        if row is None:
            raise NotFound("Produto não encontrado")
        return jsonify(serializers.ok(serializers.produto(row))), 200

    def buscar_com_filtros(self):
        filtros = schemas.parse_filtros_busca(request.args)
        limit, offset = self._paginacao()
        rows = self._produtos.buscar(limit=limit, offset=offset, **filtros)
        return jsonify(serializers.pagina(
            [serializers.produto(row) for row in rows],
            total=self._produtos.contar_busca(**filtros),
            limit=limit,
            offset=offset,
        )), 200

    def criar(self):
        dados = schemas.validar_produto(request.get_json(silent=True))
        with self._db.transaction():
            produto_id = self._produtos.criar(**dados)
        logger.info("produto criado", extra={"produto_id": produto_id})
        return jsonify(serializers.ok({"id": produto_id}, "Produto criado")), 201

    def atualizar(self, produto_id):
        if self._produtos.buscar_por_id(produto_id) is None:
            raise NotFound("Produto não encontrado")
        dados = schemas.validar_produto(request.get_json(silent=True))
        with self._db.transaction():
            self._produtos.atualizar(produto_id, **dados)
        logger.info("produto atualizado", extra={"produto_id": produto_id})
        return jsonify(serializers.ok(mensagem="Produto atualizado")), 200

    def deletar(self, produto_id):
        """Exclusao logica: o produto sai do catalogo e o historico de pedidos
        que o referencia continua legivel."""
        if self._produtos.buscar_por_id(produto_id) is None:
            raise NotFound("Produto não encontrado")
        with self._db.transaction():
            self._produtos.desativar(produto_id)
        logger.info("produto desativado", extra={"produto_id": produto_id})
        return jsonify(serializers.ok(mensagem="Produto deletado")), 200
