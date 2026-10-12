"""Envio de notificacoes, atras de uma interface.

A implementacao atual **nao envia nada** — ela registra a intencao no log, e o
nome diz isso. Antes, tres `print("ENVIANDO EMAIL: ...")` dentro do controller
faziam o log de producao afirmar que o cliente tinha sido avisado quando nenhuma
mensagem saia. Trocar por um gateway real e substituir esta classe no
composition root, sem tocar em controller nem em servico de pedido.
"""
import logging

logger = logging.getLogger(__name__)


class NotificationService:
    """Contrato que os chamadores conhecem."""

    def pedido_criado(self, pedido_id, usuario_id):
        raise NotImplementedError

    def pedido_aprovado(self, pedido_id):
        raise NotImplementedError

    def pedido_cancelado(self, pedido_id):
        raise NotImplementedError


class LoggingNotificationService(NotificationService):
    """Stub explicito: registra o evento, nao envia mensagem."""

    CANAIS = ("email", "sms", "push")

    def pedido_criado(self, pedido_id, usuario_id):
        logger.info(
            "notificacao nao enviada (stub): pedido criado",
            extra={"pedido_id": pedido_id, "usuario_id": usuario_id,
                   "canais": self.CANAIS},
        )

    def pedido_aprovado(self, pedido_id):
        logger.info(
            "notificacao nao enviada (stub): pedido aprovado",
            extra={"pedido_id": pedido_id},
        )

    def pedido_cancelado(self, pedido_id):
        logger.info(
            "notificacao nao enviada (stub): pedido cancelado",
            extra={"pedido_id": pedido_id},
        )
