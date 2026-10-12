"""Relatorio de vendas: a politica de desconto e o ticket medio.

Nenhuma das duas e propriedade de uma entidade — desconto sobre faturamento total
nao e atributo de um pedido —, por isso vivem num servico e nao no model. Antes
estavam no meio da funcao que executava as consultas, inalcancaveis sem banco.
"""
from src.models.pedido_model import (
    STATUS_APROVADO,
    STATUS_CANCELADO,
    STATUS_PENDENTE,
)

# Faixas progressivas de desconto sobre o faturamento bruto, da maior para a menor.
FAIXAS_DE_DESCONTO = (
    (10000, 0.1),
    (5000, 0.05),
    (1000, 0.02),
)
CASAS_DECIMAIS = 2


def desconto_por_faturamento(faturamento):
    """Desconto aplicavel ao faturamento. Funcao pura: testavel sem banco."""
    for limite, taxa in FAIXAS_DE_DESCONTO:
        if faturamento > limite:
            return faturamento * taxa
    return 0


def ticket_medio(faturamento, total_pedidos):
    if not total_pedidos:
        return 0
    return faturamento / total_pedidos


class RelatorioService:
    def __init__(self, pedido_model):
        self._pedidos = pedido_model

    def vendas(self):
        total_pedidos = self._pedidos.contar()
        faturamento = self._pedidos.faturamento_total()
        por_status = self._pedidos.contagem_por_status()
        desconto = desconto_por_faturamento(faturamento)

        return {
            "total_pedidos": total_pedidos,
            "faturamento_bruto": round(faturamento, CASAS_DECIMAIS),
            "desconto_aplicavel": round(desconto, CASAS_DECIMAIS),
            "faturamento_liquido": round(faturamento - desconto, CASAS_DECIMAIS),
            "pedidos_pendentes": por_status.get(STATUS_PENDENTE, 0),
            "pedidos_aprovados": por_status.get(STATUS_APROVADO, 0),
            "pedidos_cancelados": por_status.get(STATUS_CANCELADO, 0),
            "ticket_medio": round(ticket_medio(faturamento, total_pedidos), CASAS_DECIMAIS),
        }
