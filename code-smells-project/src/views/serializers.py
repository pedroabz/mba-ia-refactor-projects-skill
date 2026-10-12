"""Representacao publica das entidades — a camada View de uma API.

Um serializador por entidade, usado por todos os endpoints. Antes o mesmo
dicionario era remontado a mao em seis lugares dentro da camada de dados, o que
e como `senha` chegou a estar em dois deles e ausente no terceiro.
"""

PRODUTO_DESCONHECIDO = "Desconhecido"


def produto(row):
    return {
        "id": row["id"],
        "nome": row["nome"],
        "descricao": row["descricao"],
        "preco": row["preco"],
        "estoque": row["estoque"],
        "categoria": row["categoria"],
        "ativo": row["ativo"],
        "criado_em": row["criado_em"],
    }


def usuario(row):
    """Representacao publica do usuario. Nunca inclui credencial — nenhum
    endpoint que serializa usuario pode vazar senha ou hash."""
    return {
        "id": row["id"],
        "nome": row["nome"],
        "email": row["email"],
        "tipo": row["tipo"],
        "criado_em": row["criado_em"],
    }


def usuario_autenticado(dados):
    return {
        "id": dados["id"],
        "nome": dados["nome"],
        "email": dados["email"],
        "tipo": dados["tipo"],
    }


def agrupar_pedidos(rows):
    """Converte as linhas do JOIN pedido+item+produto em pedidos com seus itens.

    Funcao pura: recebe linhas, devolve a estrutura da resposta. A ordem segue a
    da consulta (pedido.id, item.id), portanto e deterministica.
    """
    pedidos = []
    por_id = {}
    for row in rows:
        pedido_id = row["pedido_id"]
        pedido = por_id.get(pedido_id)
        if pedido is None:
            pedido = {
                "id": pedido_id,
                "usuario_id": row["usuario_id"],
                "status": row["status"],
                "total": row["total"],
                "criado_em": row["criado_em"],
                "itens": [],
            }
            por_id[pedido_id] = pedido
            pedidos.append(pedido)

        if row["item_id"] is None:
            continue
        pedido["itens"].append({
            "produto_id": row["produto_id"],
            "produto_nome": row["produto_nome"] or PRODUTO_DESCONHECIDO,
            "quantidade": row["quantidade"],
            "preco_unitario": row["preco_unitario"],
        })
    return pedidos


# ---- envelope -----------------------------------------------------------
# Um unico formato para sucesso e um unico para erro (este ultimo produzido so
# pelo error handler). Antes `sucesso` aparecia em algumas respostas e nao em
# outras, e o cliente nao tinha como testar falha de forma confiavel.


def ok(dados=None, mensagem=None, **extra):
    corpo = {"sucesso": True}
    if dados is not None:
        corpo["dados"] = dados
    if mensagem is not None:
        corpo["mensagem"] = mensagem
    corpo.update(extra)
    return corpo


def pagina(dados, total, limit, offset, **extra):
    return ok(dados, total=total, limit=limit, offset=offset, **extra)
