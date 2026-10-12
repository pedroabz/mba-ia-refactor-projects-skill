"""Superficie de entrada: endereco, metodo, guarda e o controller que atende.

Cada rota e uma linha de delegacao. Nenhuma regra de negocio, nenhuma consulta e
nenhuma validacao alem do que o proprio transporte oferece (o conversor `<int:>`).
O controle de acesso e aplicado aqui, e nao dentro do controller, para que nao
exista caminho que chegue ao controller sem passar pela guarda.
"""
from flask import Blueprint

TIPO_ADMIN = "admin"


def register_routes(app, controllers, guard, limiter, settings):
    produto = controllers["produto"]
    usuario = controllers["usuario"]
    pedido = controllers["pedido"]
    relatorio = controllers["relatorio"]
    sistema = controllers["sistema"]

    somente_admin = guard.require_role(TIPO_ADMIN)
    autenticado = guard.require_auth
    limite_login = limiter.limit("login", settings.LOGIN_RATE_LIMIT)
    limite_admin = limiter.limit("admin", settings.ADMIN_RATE_LIMIT)

    # ---- publico -------------------------------------------------------
    sistema_bp = Blueprint("sistema", __name__)
    sistema_bp.add_url_rule("/", "index", sistema.index, methods=["GET"])
    sistema_bp.add_url_rule("/health", "health_check", sistema.health, methods=["GET"])

    produtos_bp = Blueprint("produtos", __name__)
    produtos_bp.add_url_rule(
        "/produtos", "listar_produtos", produto.listar, methods=["GET"])
    produtos_bp.add_url_rule(
        "/produtos/busca", "buscar_produtos", produto.buscar_com_filtros, methods=["GET"])
    produtos_bp.add_url_rule(
        "/produtos/<int:produto_id>", "buscar_produto", produto.buscar, methods=["GET"])

    # ---- catalogo: escrita restrita a administracao ---------------------
    produtos_bp.add_url_rule(
        "/produtos", "criar_produto", somente_admin(produto.criar), methods=["POST"])
    produtos_bp.add_url_rule(
        "/produtos/<int:produto_id>", "atualizar_produto",
        somente_admin(produto.atualizar), methods=["PUT"])
    produtos_bp.add_url_rule(
        "/produtos/<int:produto_id>", "deletar_produto",
        somente_admin(produto.deletar), methods=["DELETE"])

    # ---- usuarios ------------------------------------------------------
    usuarios_bp = Blueprint("usuarios", __name__)
    usuarios_bp.add_url_rule(
        "/usuarios", "listar_usuarios", somente_admin(usuario.listar), methods=["GET"])
    usuarios_bp.add_url_rule(
        "/usuarios/<int:usuario_id>", "buscar_usuario",
        somente_admin(usuario.buscar), methods=["GET"])
    usuarios_bp.add_url_rule(
        "/usuarios", "criar_usuario", usuario.criar, methods=["POST"])
    usuarios_bp.add_url_rule(
        "/login", "login", limite_login(usuario.login), methods=["POST"])

    # ---- pedidos -------------------------------------------------------
    pedidos_bp = Blueprint("pedidos", __name__)
    pedidos_bp.add_url_rule(
        "/pedidos", "criar_pedido", autenticado(pedido.criar), methods=["POST"])
    pedidos_bp.add_url_rule(
        "/pedidos", "listar_todos_pedidos",
        somente_admin(pedido.listar_todos), methods=["GET"])
    pedidos_bp.add_url_rule(
        "/pedidos/usuario/<int:usuario_id>", "listar_pedidos_usuario",
        autenticado(pedido.listar_do_usuario), methods=["GET"])
    pedidos_bp.add_url_rule(
        "/pedidos/<int:pedido_id>/status", "atualizar_status_pedido",
        somente_admin(pedido.atualizar_status), methods=["PUT"])

    # ---- relatorios ----------------------------------------------------
    relatorios_bp = Blueprint("relatorios", __name__)
    relatorios_bp.add_url_rule(
        "/relatorios/vendas", "relatorio_vendas",
        somente_admin(relatorio.vendas), methods=["GET"])

    # ---- administracao -------------------------------------------------
    # `/admin/query`, que executava SQL arbitrario enviado pelo cliente, nao foi
    # reescrito: foi removido. Nao existe versao segura desse endpoint.
    admin_bp = Blueprint("admin", __name__)
    admin_bp.add_url_rule(
        "/admin/reset-db", "reset_database",
        limite_admin(somente_admin(sistema.resetar_banco)), methods=["POST"])

    for blueprint in (sistema_bp, produtos_bp, usuarios_bp, pedidos_bp,
                      relatorios_bp, admin_bp):
        app.register_blueprint(blueprint)
