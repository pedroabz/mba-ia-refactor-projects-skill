"""Fluxo HTTP dos casos de uso de usuario e da autenticacao."""
import logging

from flask import jsonify, request

from src.errors import Conflict, NotFound, Unauthorized
from src.views import schemas, serializers

logger = logging.getLogger(__name__)


class UsuarioController:
    def __init__(self, db, usuario_model, auth_service, settings):
        self._db = db
        self._usuarios = usuario_model
        self._auth = auth_service
        self._settings = settings

    def listar(self):
        limit, offset = schemas.parse_paginacao(
            request.args,
            self._settings.DEFAULT_PAGE_SIZE,
            self._settings.MAX_PAGE_SIZE,
        )
        rows = self._usuarios.listar(limit, offset)
        return jsonify(serializers.pagina(
            [serializers.usuario(row) for row in rows],
            total=self._usuarios.contar(),
            limit=limit,
            offset=offset,
        )), 200

    def buscar(self, usuario_id):
        row = self._usuarios.buscar_por_id(usuario_id)
        if row is None:
            raise NotFound("Usuário não encontrado")
        return jsonify(serializers.ok(serializers.usuario(row))), 200

    def criar(self):
        dados = schemas.validar_usuario(request.get_json(silent=True))
        if self._usuarios.email_cadastrado(dados["email"]):
            raise Conflict("Email já cadastrado")

        senha_hash = self._auth.hash_senha(dados["senha"])
        with self._db.transaction():
            usuario_id = self._usuarios.criar(dados["nome"], dados["email"], senha_hash)

        # Identificador, nunca o email nem a senha.
        logger.info("usuario criado", extra={"usuario_id": usuario_id})
        return jsonify(serializers.ok({"id": usuario_id})), 201

    def login(self):
        credenciais = schemas.validar_login(request.get_json(silent=True))
        usuario = self._auth.autenticar(credenciais["email"], credenciais["senha"])
        if usuario is None:
            logger.warning("login recusado")
            raise Unauthorized("Email ou senha inválidos")

        logger.info("login aceito", extra={"usuario_id": usuario["id"]})
        return jsonify(serializers.ok(
            serializers.usuario_autenticado(usuario),
            "Login OK",
            token=self._auth.emitir_token(usuario),
        )), 200
