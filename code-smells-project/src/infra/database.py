"""Fabrica de conexoes SQLite com ciclo de vida por requisicao.

Substitui a conexao global mutavel: cada requisicao recebe a sua conexao, o
framework a fecha no teardown, e nenhuma transacao abandonada sobrevive para ser
efetivada por uma requisicao posterior.
"""
import logging
import sqlite3
from contextlib import contextmanager

from flask import g

logger = logging.getLogger(__name__)

_CONNECTION_KEY = "_db_connection"


class Database:
    """Dono do acesso ao banco. Recebe o caminho; nunca o descobre sozinho."""

    def __init__(self, path):
        self._path = path

    @property
    def path(self):
        return self._path

    def connect(self):
        """Abre uma conexao nova e isolada. Use fora do ciclo de requisicao."""
        connection = sqlite3.connect(self._path)
        connection.row_factory = sqlite3.Row
        # Integridade referencial no SQLite e opt-in por conexao: sem isto as
        # chaves estrangeiras declaradas no schema nao sao aplicadas.
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def init_app(self, app):
        """Registra o fechamento da conexao no fim de cada contexto de aplicacao."""

        @app.teardown_appcontext
        def _close_connection(exception):  # pragma: no cover - hook do framework
            connection = g.pop(_CONNECTION_KEY, None)
            if connection is None:
                return
            if exception is not None:
                connection.rollback()
            connection.close()

    def connection(self):
        """Conexao desta requisicao, criada na primeira chamada e reutilizada."""
        connection = getattr(g, _CONNECTION_KEY, None)
        if connection is None:
            connection = self.connect()
            setattr(g, _CONNECTION_KEY, connection)
        return connection

    @contextmanager
    def transaction(self):
        """Unidade de trabalho: efetiva no fim, desfaz em qualquer excecao."""
        connection = self.connection()
        try:
            yield connection
        except Exception:
            connection.rollback()
            logger.warning("transacao desfeita")
            raise
        else:
            connection.commit()
