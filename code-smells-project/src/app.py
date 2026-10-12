"""Composition root: o unico lugar que monta a aplicacao.

Carrega a configuracao, cria as dependencias, injeta cada camada na seguinte,
registra os middlewares e as rotas. Nao define handler, nao executa consulta e
nao cria schema por conta propria — chama o modulo que faz isso.
"""
import logging

from flask import Flask
from flask_cors import CORS

from src.config.logging_config import configure_logging
from src.config.settings import load_settings
from src.controllers.pedido_controller import PedidoController
from src.controllers.produto_controller import ProdutoController
from src.controllers.relatorio_controller import RelatorioController
from src.controllers.sistema_controller import SistemaController
from src.controllers.usuario_controller import UsuarioController
from src.infra.database import Database
from src.infra.schema import create_schema, seed_if_empty
from src.middlewares.auth import AuthGuard
from src.middlewares.error_handler import register_error_handlers
from src.middlewares.rate_limit import RateLimiter
from src.middlewares.request_log import register_request_logging
from src.models.manutencao_model import ManutencaoModel
from src.models.pedido_model import PedidoModel
from src.models.produto_model import ProdutoModel
from src.models.usuario_model import UsuarioModel
from src.services.auth_service import AuthService
from src.services.notification_service import LoggingNotificationService
from src.services.pedido_service import PedidoService
from src.services.relatorio_service import RelatorioService
from src.views.routes import register_routes

logger = logging.getLogger(__name__)


def bootstrap_database(db, seed=True):
    """Garante schema e carga inicial. Passo explicito, fora do ciclo de leitura."""
    connection = db.connect()
    try:
        create_schema(connection)
        if seed:
            seed_if_empty(connection, AuthService.hash_senha)
    finally:
        connection.close()


def create_app(settings=None):
    settings = settings or load_settings()
    configure_logging(settings.LOG_LEVEL)

    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=settings.SECRET_KEY,
        DEBUG=settings.DEBUG,
        MAX_CONTENT_LENGTH=settings.MAX_CONTENT_LENGTH,
    )

    # Origens explicitas, nunca curinga.
    CORS(app, resources={r"/*": {"origins": settings.CORS_ORIGINS}})

    # Persistencia: uma conexao por requisicao, fechada no teardown.
    db = Database(settings.DATABASE_PATH)
    db.init_app(app)
    bootstrap_database(db, seed=settings.SEED_ON_BOOT)

    # Models recebem o banco; nunca o constroem.
    produto_model = ProdutoModel(db)
    usuario_model = UsuarioModel(db)
    pedido_model = PedidoModel(db)
    manutencao_model = ManutencaoModel(db)

    # Services recebem models e colaboradores externos.
    auth_service = AuthService(usuario_model, settings.SECRET_KEY, settings.TOKEN_TTL_SECONDS)
    notification_service = LoggingNotificationService()
    pedido_service = PedidoService(
        db, pedido_model, produto_model, usuario_model, notification_service
    )
    relatorio_service = RelatorioService(pedido_model)

    # Controllers recebem services e models.
    controllers = {
        "produto": ProdutoController(db, produto_model, settings),
        "usuario": UsuarioController(db, usuario_model, auth_service, settings),
        "pedido": PedidoController(pedido_model, pedido_service, settings),
        "relatorio": RelatorioController(relatorio_service),
        "sistema": SistemaController(manutencao_model, settings),
    }

    guard = AuthGuard(auth_service)
    limiter = RateLimiter(enabled=settings.RATE_LIMIT_ENABLED)

    register_request_logging(app)
    register_routes(app, controllers, guard, limiter, settings)
    register_error_handlers(app)

    logger.info(
        "aplicacao montada",
        extra={"debug": settings.DEBUG, "banco": settings.DATABASE_PATH},
    )
    return app
