"""Composition root.

Builds the application and nothing else: load config, configure logging,
initialize extensions, register the middleware chain, register routes. It
defines no route handler, runs no query and creates no schema — the previous
entry point did all three, and executed `db.create_all()` at import time.

`create_app` is a factory rather than a module-level `app`, which is what makes
it possible to build a second instance against a different database. That is
also what makes the application testable without touching the real file.
"""
from flask import Flask
from flask_cors import CORS

from src.config.logging_config import configure_logging, get_logger
from src.config.settings import Settings
from src.config.settings import settings as default_settings
from src.extensions import db, limiter, migrate
from src.middlewares.error_handler import register_error_handlers
from src.routes import ALL_BLUEPRINTS


def create_app(settings: Settings | None = None) -> Flask:
    settings = settings or default_settings
    settings.validate()

    configure_logging(settings.LOG_LEVEL)
    logger = get_logger(__name__)

    app = Flask(__name__)

    app.config["SECRET_KEY"] = settings.SECRET_KEY
    app.config["SQLALCHEMY_DATABASE_URI"] = settings.DATABASE_URL
    app.config["SQLALCHEMY_ECHO"] = settings.SQLALCHEMY_ECHO
    app.config["DEBUG"] = settings.DEBUG
    # Bound the request body: five endpoints accept one and nothing capped it.
    app.config["MAX_CONTENT_LENGTH"] = settings.MAX_CONTENT_LENGTH
    app.config["SETTINGS"] = settings

    # Explicit origin allowlist. The previous `CORS(app)` sent
    # Access-Control-Allow-Origin: * on every route, including /login.
    CORS(app, origins=settings.CORS_ORIGINS)

    db.init_app(app)
    migrate.init_app(app, db)
    limiter.init_app(app)

    # Importing the package registers every mapper before anything queries.
    import src.models  # noqa: F401

    # Rate limits are declared on the view functions in the route modules, so
    # importing the blueprints is what attaches them.
    for blueprint in ALL_BLUEPRINTS:
        app.register_blueprint(blueprint)

    # Registered after the routes so it is the last thing in the chain.
    register_error_handlers(app)

    logger.info(
        "application composed (debug=%s, database=%s)",
        settings.DEBUG, settings.DATABASE_URL,
    )
    return app
