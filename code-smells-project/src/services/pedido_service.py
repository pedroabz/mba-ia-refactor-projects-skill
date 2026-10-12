"""Caso de uso do pedido: checkout e transicao de status.

A regra atravessa tres entidades (pedido, item, produto), portanto nao pertence a
nenhum model — vive aqui. Duas garantias que o codigo anterior nao tinha:

1. Toda validacao que pode falhar acontece **antes** da primeira escrita, e as
   escritas correm dentro de uma transacao que desfaz tudo em caso de erro.
2. O cancelamento devolve o estoque de fato. Antes isso existia apenas como
   texto de um `print`.
"""
import logging

from src.errors import BusinessRuleError, NotFound
from src.models.pedido_model import STATUS_APROVADO, STATUS_CANCELADO, STATUS_PENDENTE

logger = logging.getLogger(__name__)


class PedidoService:
    def __init__(self, db, pedido_model, produto_model, usuario_model, notification_service):
        self._db = db
        self._pedidos = pedido_model
        self._produtos = produto_model
        self._usuarios = usuario_model
        self._notificacoes = notification_service

    # ---- checkout ------------------------------------------------------

    def criar(self, usuario_id, itens):
        """Cria o pedido inteiro ou nada. Devolve {pedido_id, total}."""
        if not self._usuarios.existe(usuario_id):
            raise BusinessRuleError("Usuário não encontrado")

        reservas = self._conferir_itens(itens)
        total = 0
        for reserva in reservas:
            total = total + (reserva["preco_unitario"] * reserva["quantidade"])

        with self._db.transaction():
            pedido_id = self._pedidos.criar(usuario_id, total, status=STATUS_PENDENTE)
            for reserva in reservas:
                self._pedidos.adicionar_item(
                    pedido_id,
                    reserva["produto_id"],
                    reserva["quantidade"],
                    reserva["preco_unitario"],
                )
                self._produtos.ajustar_estoque(reserva["produto_id"], -reserva["quantidade"])

        logger.info(
            "pedido criado",
            extra={"pedido_id": pedido_id, "usuario_id": usuario_id, "total": total},
        )
        self._notificacoes.pedido_criado(pedido_id, usuario_id)
        return {"pedido_id": pedido_id, "total": total}

    def _conferir_itens(self, itens):
        """Confere existencia e estoque de todos os itens antes de qualquer escrita."""
        reservas = []
        for item in itens:
            produto = self._produtos.buscar_por_id(item["produto_id"])
            if produto is None:
                raise BusinessRuleError(f"Produto {item['produto_id']} não encontrado")
            if produto["estoque"] < item["quantidade"]:
                raise BusinessRuleError(f"Estoque insuficiente para {produto['nome']}")
            reservas.append({
                "produto_id": produto["id"],
                "quantidade": item["quantidade"],
                "preco_unitario": produto["preco"],
            })
        return reservas

    # ---- transicao de status -------------------------------------------

    def atualizar_status(self, pedido_id, novo_status):
        """Aplica o novo status e os efeitos que ele implica."""
        pedido = self._pedidos.buscar_por_id(pedido_id)
        if pedido is None:
            raise NotFound("Pedido não encontrado")

        status_anterior = pedido["status"]
        devolver_estoque = (
            novo_status == STATUS_CANCELADO and status_anterior != STATUS_CANCELADO
        )

        with self._db.transaction():
            self._pedidos.atualizar_status(pedido_id, novo_status)
            if devolver_estoque:
                for item in self._pedidos.itens_do_pedido(pedido_id):
                    self._produtos.ajustar_estoque(item["produto_id"], item["quantidade"])

        logger.info(
            "status do pedido atualizado",
            extra={"pedido_id": pedido_id, "de": status_anterior, "para": novo_status,
                   "estoque_devolvido": devolver_estoque},
        )

        if novo_status == STATUS_APROVADO:
            self._notificacoes.pedido_aprovado(pedido_id)
        if devolver_estoque:
            self._notificacoes.pedido_cancelado(pedido_id)
        return True
