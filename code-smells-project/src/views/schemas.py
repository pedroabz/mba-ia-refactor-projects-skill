"""Validacao na fronteira: o que a aplicacao aceita, declarado em um lugar.

A validacao de produto e a mesma funcao para criacao e atualizacao — antes eram
duas copias, e a da atualizacao tinha esquecido o tamanho do nome e a lista de
categorias, de modo que um PUT colocava o produto num estado que o POST recusava.

Os tipos sao conferidos antes das comparacoes, para que entrada malformada seja
400 com mensagem util em vez de 500 com texto de excecao.
"""
from src.errors import ValidationError
from src.models.pedido_model import STATUS_VALIDOS
from src.models.produto_model import (
    CATEGORIAS_VALIDAS,
    NOME_TAMANHO_MAXIMO,
    NOME_TAMANHO_MINIMO,
)
from src.services.auth_service import SENHA_TAMANHO_MINIMO

CATEGORIA_PADRAO = "geral"
EMAIL_TAMANHO_MAXIMO = 254


def _corpo(payload):
    if not payload or not isinstance(payload, dict):
        raise ValidationError("Dados inválidos")
    return payload


def _numero(valor, nome_do_campo):
    if isinstance(valor, bool) or not isinstance(valor, (int, float)):
        raise ValidationError(f"{nome_do_campo} deve ser um número")
    return valor


def _inteiro(valor, nome_do_campo):
    if isinstance(valor, bool) or not isinstance(valor, int):
        raise ValidationError(f"{nome_do_campo} deve ser um número inteiro")
    return valor


def _texto(valor, nome_do_campo):
    if not isinstance(valor, str):
        raise ValidationError(f"{nome_do_campo} deve ser um texto")
    return valor


# ---- produto ------------------------------------------------------------


def validar_produto(payload):
    """Unica fonte das regras de produto. Usada por criacao e atualizacao."""
    dados = _corpo(payload)

    if "nome" not in dados:
        raise ValidationError("Nome é obrigatório")
    if "preco" not in dados:
        raise ValidationError("Preço é obrigatório")
    if "estoque" not in dados:
        raise ValidationError("Estoque é obrigatório")

    nome = _texto(dados["nome"], "Nome").strip()
    descricao = _texto(dados.get("descricao", ""), "Descrição")
    preco = _numero(dados["preco"], "Preço")
    estoque = _inteiro(dados["estoque"], "Estoque")
    categoria = _texto(dados.get("categoria") or CATEGORIA_PADRAO, "Categoria")

    if preco < 0:
        raise ValidationError("Preço não pode ser negativo")
    if estoque < 0:
        raise ValidationError("Estoque não pode ser negativo")
    if len(nome) < NOME_TAMANHO_MINIMO:
        raise ValidationError("Nome muito curto")
    if len(nome) > NOME_TAMANHO_MAXIMO:
        raise ValidationError("Nome muito longo")
    if categoria not in CATEGORIAS_VALIDAS:
        raise ValidationError(
            "Categoria inválida. Válidas: " + str(list(CATEGORIAS_VALIDAS))
        )

    return {
        "nome": nome,
        "descricao": descricao,
        "preco": preco,
        "estoque": estoque,
        "categoria": categoria,
    }


# ---- usuario e login ----------------------------------------------------


def validar_usuario(payload):
    dados = _corpo(payload)

    nome = dados.get("nome") or ""
    email = dados.get("email") or ""
    senha = dados.get("senha") or ""

    if not nome or not email or not senha:
        raise ValidationError("Nome, email e senha são obrigatórios")

    nome = _texto(nome, "Nome").strip()
    email = _texto(email, "Email").strip().lower()
    senha = _texto(senha, "Senha")

    if "@" not in email or "." not in email.split("@")[-1] or len(email) > EMAIL_TAMANHO_MAXIMO:
        raise ValidationError("Email inválido")
    if len(senha) < SENHA_TAMANHO_MINIMO:
        raise ValidationError(
            f"Senha deve ter ao menos {SENHA_TAMANHO_MINIMO} caracteres"
        )

    return {"nome": nome, "email": email, "senha": senha}


def validar_login(payload):
    dados = payload or {}
    email = dados.get("email") or ""
    senha = dados.get("senha") or ""
    if not email or not senha:
        raise ValidationError("Email e senha são obrigatórios")
    return {"email": _texto(email, "Email").strip().lower(), "senha": _texto(senha, "Senha")}


# ---- pedido -------------------------------------------------------------


def validar_pedido(payload):
    dados = _corpo(payload)

    usuario_id = dados.get("usuario_id")
    itens = dados.get("itens") or []

    if usuario_id is None:
        raise ValidationError("Usuario ID é obrigatório")
    usuario_id = _inteiro(usuario_id, "Usuario ID")
    if usuario_id <= 0:
        raise ValidationError("Usuario ID inválido")

    if not itens:
        raise ValidationError("Pedido deve ter pelo menos 1 item")
    if not isinstance(itens, list):
        raise ValidationError("Itens deve ser uma lista")

    validados = []
    for posicao, item in enumerate(itens, start=1):
        if not isinstance(item, dict):
            raise ValidationError(f"Item {posicao} inválido")
        if "produto_id" not in item:
            raise ValidationError(f"Item {posicao}: produto_id é obrigatório")
        if "quantidade" not in item:
            raise ValidationError(f"Item {posicao}: quantidade é obrigatória")

        produto_id = _inteiro(item["produto_id"], f"Item {posicao}: produto_id")
        quantidade = _inteiro(item["quantidade"], f"Item {posicao}: quantidade")
        if produto_id <= 0:
            raise ValidationError(f"Item {posicao}: produto_id inválido")
        if quantidade < 1:
            # Quantidade negativa passava pela conferencia de estoque, reduzia o
            # total e aumentava o estoque do produto.
            raise ValidationError(f"Item {posicao}: quantidade deve ser maior que zero")

        validados.append({"produto_id": produto_id, "quantidade": quantidade})

    return {"usuario_id": usuario_id, "itens": validados}


def validar_status_pedido(payload):
    dados = payload or {}
    status = dados.get("status") or ""
    if status not in STATUS_VALIDOS:
        raise ValidationError("Status inválido")
    return status


# ---- parametros de consulta --------------------------------------------


def parse_paginacao(args, tamanho_padrao, tamanho_maximo):
    """Limite e deslocamento, sempre restringidos no servidor.

    Um `limit` enviado pelo cliente e um pedido, nao uma autorizacao: o valor e
    limitado ao maximo configurado.
    """
    limit = args.get("limit", default=tamanho_padrao, type=int) or tamanho_padrao
    offset = args.get("offset", default=0, type=int) or 0
    limit = min(max(limit, 1), tamanho_maximo)
    offset = max(offset, 0)
    return limit, offset


def _preco(args, nome_do_campo):
    bruto = args.get(nome_do_campo)
    if bruto is None or bruto == "":
        return None
    try:
        return float(bruto)
    except ValueError:
        raise ValidationError(f"{nome_do_campo} deve ser um número") from None


def parse_filtros_busca(args):
    return {
        "termo": (args.get("q") or "").strip(),
        "categoria": (args.get("categoria") or "").strip() or None,
        "preco_min": _preco(args, "preco_min"),
        "preco_max": _preco(args, "preco_max"),
    }
